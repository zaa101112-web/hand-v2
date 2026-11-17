"""One path owns one gesture. Geometry is pure and timestamps are supplied."""
import math

from .features import TimeEMA,distance
from .models import Gesture


class MotionRecognizer:
    def __init__(self):self.reset()

    def reset(self):
        self.key=None;self.since=None;self.path=[];self.fired=False
        self.ema=TimeEMA(60);self.curved=False;self.axis=None
        self.initial_direction=None;self.direction_anchor=None;self.curve_reason=''
        self.pose_since=None;self.anchor=None;self.anchor_at=None
        self.preparation_resets=0

    def update(self,feature,at,width,height):
        key=(feature.hand_id,feature.pose)
        if key!=self.key:
            self.reset();self.key=key;self.pose_since=at
        point=self.ema.update(feature.pointer,at)
        previous=self.path[-1][1] if self.path else None
        self.path.append((at,point));self.path=self.path[-256:]
        if self.fired:return None,1,'RELEASE_REQUIRED'
        if self.since is not None and self._settled(at,width,height):
            # Finger extension/repositioning may start a short path before the
            # intended swipe. A genuine pause ends that unfinished path. Never
            # reset a fired path here: release still owns command rearming.
            self.since=None;self.path=[(at,point)]
            self.anchor=point;self.anchor_at=at;self.direction_anchor=point
            self.initial_direction=None;self.curved=False;self.curve_reason='';self.axis=None
            self.preparation_resets+=1
            return None,0,'MOTION_READY'
        if self.anchor is None:
            self.anchor=point;self.anchor_at=at
            self.direction_anchor=point
            return None,0,'MOTION_READY'
        if self.since is None:
            # Start the motion clock after actual displacement, not when the
            # user first forms the pose. Stationary samples refresh its anchor.
            if distance(point,self.anchor)<.02:
                if previous is not None and distance(point,previous)<.002:
                    self.anchor=point;self.anchor_at=at;self.path=[(at,point)]
                    self.direction_anchor=point
                return None,0,'MOTION_READY'
            self.since=self.anchor_at
        elapsed=at-self.since
        start=self.path[0][1];dx,dy=point[0]-start[0],point[1]-start[1]
        length=sum(distance(a[1],b[1]) for a,b in zip(self.path,self.path[1:]))
        straight=math.hypot(dx,dy)/length if length>1e-9 else 0
        if not self.curved and length>.03 and straight<.90:
            self.curved=True;self.curve_reason='NON_STRAIGHT_PATH'
        if self.direction_anchor is not None:
            sx,sy=(point[0]-self.direction_anchor[0])*width,(point[1]-self.direction_anchor[1])*height
            # A one-pixel vector has no reliable direction during a slowdown.
            # Measure turns over a resolution-scaled span, retaining the same
            # 25deg rejection before any swipe can be emitted.
            if math.hypot(sx,sy)>=.025*min(width,height):
                direction=math.atan2(sy,sx)
                if self.initial_direction is None:self.initial_direction=direction
                elif not self.curved and abs(math.atan2(math.sin(direction-self.initial_direction),math.cos(direction-self.initial_direction)))>math.radians(25):
                    self.curved=True;self.curve_reason='DIRECTION_CHANGE'
                self.direction_anchor=point
        if self.axis is None and max(abs(dx),abs(dy))>=.04:
            if abs(dx)>=1.8*abs(dy):self.axis='x'
            elif abs(dy)>=1.8*abs(dx):self.axis='y'
        if elapsed> (600 if feature.pose=='V' else 2000):
            self.fired=True;return None,0,'MOTION_TOO_SLOW'
        axis=self.axis if feature.pose=='V' else 'x'
        primary,secondary=(dx,dy) if axis=='x' else (dy,dx)
        if axis and at-self.pose_since>=120 and 150<=elapsed<=600 and abs(primary)>=.15 and abs(primary)>=1.8*abs(secondary) and straight>=.90 and not self.curved:
            self.fired=True
            if feature.pose=='INDEX':gesture=Gesture.LEFT if dx<0 else Gesture.RIGHT
            elif axis=='x':gesture=Gesture.TAB_LEFT if dx<0 else Gesture.TAB_RIGHT
            else:gesture=Gesture.PAGE_UP if dy<0 else Gesture.PAGE_DOWN
            return gesture,1,'CONFIRMED'
        if feature.pose=='INDEX' and self.curved and 600<=elapsed<=2000 and self._circle(width,height):
            self.fired=True;return Gesture.CIRCLE,1,'CONFIRMED'
        return None,min(1,max(abs(dx),abs(dy))/.15),'CIRCLE_CANDIDATE' if self.curved else 'MOTION_IN_PROGRESS'

    def _settled(self,at,width,height):
        # Bound total excursion, not each frame's velocity: a slow continuous
        # movement or a circle must not be mistaken for a stationary pause.
        recent=[]
        for timestamp,point in reversed(self.path):
            recent.append((point[0]*width,point[1]*height))
            if at-timestamp>=180:
                span_x=max(p[0] for p in recent)-min(p[0] for p in recent)
                span_y=max(p[1] for p in recent)-min(p[1] for p in recent)
                return math.hypot(span_x,span_y)<=.008*min(width,height)
        return False

    def _circle(self,width,height):
        points=[(p[0]*width,p[1]*height) for _,p in self.path]
        if len(points)<8:return False
        center=((min(p[0] for p in points)+max(p[0] for p in points))/2,
                (min(p[1] for p in points)+max(p[1] for p in points))/2)
        radii=[distance(p,center) for p in points];radius=sum(radii)/len(radii)
        if not .04*min(width,height)<=radius<=.20*min(width,height):return False
        cv=math.sqrt(sum((r-radius)**2 for r in radii)/len(radii))/radius
        if cv>.35 or distance(points[0],points[-1])>.5*radius:return False
        angles=[math.atan2(p[1]-center[1],p[0]-center[0]) for p in points]
        turns=[math.atan2(math.sin(b-a),math.cos(b-a)) for a,b in zip(angles,angles[1:])]
        total=sum(turns)
        return math.radians(300)<=abs(total)<=math.radians(420) and abs(total)>=.9*sum(abs(t) for t in turns)
