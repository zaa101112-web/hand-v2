from .features import TimeEMA,angle,distance
from .models import Gesture


class FistOpenRecognizer:
    def __init__(self):self.reset()
    def reset(self):
        self.hand_id=None;self.since=None;self.qualified=None;self.open_since=None;self.fired=False
        self.eligible=False
    def update(self,feature,at,ready=True):
        if self.hand_id!=feature.hand_id:
            self.reset();self.hand_id=feature.hand_id
        if feature.pose=='FIST':
            if self.open_since is not None or self.fired:
                self.reset();self.hand_id=feature.hand_id
            if self.since is None:self.since=at;self.eligible=ready
            if self.qualified is None and at-self.since>=250:self.qualified=at
        elif feature.pose=='OPEN':
            if self.qualified is None:
                self.reset();return None
            if self.qualified is not None and not self.fired:
                if self.open_since is None:
                    if at-self.qualified>1200:
                        self.reset();return None
                    self.open_since=at
                if at-self.open_since>=150:
                    self.fired=True
                    # OPEN may make the controller ready while this sequence
                    # is still being measured. Eligibility belongs to its
                    # starting FIST, never to a later neutral-timer callback.
                    return Gesture.FIST_OPEN if self.eligible else None
        else:self.reset()
        return None


class PairRecognizer:
    def __init__(self,pinch_enter=.30,pinch_exit=.45,zoom_step_ratio=1.15,smoothing_tau_ms=60):
        self.pinch_enter=pinch_enter;self.pinch_exit=pinch_exit;self.zoom_step_ratio=zoom_step_ratio
        self.smoothing_tau_ms=smoothing_tau_ms;self.reset()
    def reset(self):
        self.key=None;self.pinch={};self.pinch_since=None;self.baseline=None
        self.zoom_direction=None;self.zoom_since=None;self.ema=TimeEMA(self.smoothing_tau_ms)
        self.l_since=None;self.l_fired=False

    def update(self,features,hands,width,height,at,ready=True):
        key=tuple(sorted(f.hand_id for f in features))
        if key!=self.key:self.reset();self.key=key
        centers=[(f.center[0]*width,f.center[1]*height) for f in features]
        separation=distance(*centers);scale=sum(f.palm_size for f in features)/2
        if self._is_frame(features,hands,width,height,separation,scale):
            self.pinch={};self.pinch_since=None;self.baseline=None;self.ema.reset()
            self.zoom_direction=None;self.zoom_since=None
            if self.l_since is None:self.l_since=at
            progress=min(1,(at-self.l_since)/800)
            gesture=None
            if progress>=1 and not self.l_fired:self.l_fired=True;gesture=Gesture.FRAME
            return gesture,progress,'L_FRAME'
        self.l_since=None;self.l_fired=False
        for f in features:
            previous=self.pinch.get(f.hand_id,False)
            self.pinch[f.hand_id]=f.palm_size>=20 and (f.pinch_ratio<self.pinch_exit if previous else f.pinch_ratio<=self.pinch_enter)
        if not all(self.pinch.values()):
            self.pinch_since=None;self.baseline=None;self.ema.reset();self.zoom_direction=None;self.zoom_since=None
            return None,0,'PINCH_RELEASE'
        smoothed=self.ema.update((separation,),at)[0]
        if self.baseline is None:
            if separation<1.5*scale:
                self.pinch_since=None;return None,0,'HANDS_TOO_CLOSE'
            if self.pinch_since is None:self.pinch_since=at
            if at-self.pinch_since>=120:self.baseline=smoothed
            return None,min(1,(at-self.pinch_since)/120),'PINCH_BASELINE'
        ratio=smoothed/self.baseline;raw_ratio=separation/self.baseline
        # Require physical displacement as well as filtered evidence. After a
        # step, EMA lag must neither add another step nor produce a reversal.
        direction=(Gesture.ZOOM_IN if min(ratio,raw_ratio)>=self.zoom_step_ratio else
                   Gesture.ZOOM_OUT if max(ratio,raw_ratio)<=1/self.zoom_step_ratio else None)
        if direction!=self.zoom_direction:
            self.zoom_direction=direction;self.zoom_since=at if direction else None
        if ready and direction and at-self.zoom_since>=80:
            self.baseline=separation;self.zoom_direction=None;self.zoom_since=None
            return direction,1,'CONFIRMED'
        return None,0 if direction is None else min(1,(at-self.zoom_since)/80),'PINCH_ZOOM'

    @staticmethod
    def _is_frame(features,hands,width,height,separation,scale):
        if not all(f.pose=='L' for f in features) or not 1.5*scale<=separation<=6*scale:return False
        vectors=[]
        for hand in hands:
            p=[(lm.x*width,lm.y*height) for lm in hand.landmarks]
            thumb=tuple(a-b for a,b in zip(p[4],p[2]));index=tuple(a-b for a,b in zip(p[8],p[5]))
            opening=angle(thumb,(0,0),index)
            norm=distance(index,(0,0))
            if opening is None or not 50<=opening<=130 or norm<1:return False
            vectors.append(tuple(x/norm for x in index))
        return sum(a*b for a,b in zip(*vectors))<=-.5
