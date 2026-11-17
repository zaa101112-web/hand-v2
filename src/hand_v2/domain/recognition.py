from dataclasses import dataclass
from .features import describe_hand,FingerState
from .models import Gesture
from .motion import MotionRecognizer
from .sequences import PairRecognizer,FistOpenRecognizer


@dataclass(frozen=True,slots=True)
class Recognition:
    gesture: Gesture | None = None
    hand_ids: tuple[str,...] = ()
    neutral: bool = False
    candidate: str = '손동작 대기'
    progress: float = 0.0
    reason: str = ''


class GestureRecognizer:
    def __init__(self,settings=None):
        self.settings=settings or {}
        self.epoch=None;self.last_at=None
        self.reset()

    def reset(self):
        self._hold_key=None;self._hold_since=None;self._hold_fired=False
        s=self.settings
        self.motion=MotionRecognizer(s.get('swipe_distance',.15),s.get('smoothing_tau_ms',60))
        self.pair=PairRecognizer(s.get('pinch_enter',.30),s.get('pinch_exit',.45),s.get('zoom_step_ratio',1.15),s.get('smoothing_tau_ms',60))
        self.fist=FistOpenRecognizer()

    def _hold(self,key,at,ms,gesture,label):
        if key!=self._hold_key:
            self._hold_key=key;self._hold_since=at;self._hold_fired=False
        progress=min(1,(at-self._hold_since)/ms)
        event=None
        if progress>=1 and not self._hold_fired:
            event=gesture;self._hold_fired=True
        return Recognition(event,(key[1],),False,label,progress)

    def process(self,frame,active,ready=True):
        at=frame.captured_at_ms
        if frame.camera_epoch!=self.epoch:
            self.reset();self.last_at=None;self.epoch=frame.camera_epoch
        if self.last_at is not None and at<=self.last_at:
            return Recognition(reason='STALE_FRAME')
        if self.last_at is not None and at-self.last_at>100:self.reset()
        self.last_at=at
        features=tuple(describe_hand(h,frame.image_width,frame.image_height) for h in frame.hands)
        if not features:
            self.reset();return Recognition(candidate='손 없음',reason='NO_HAND')
        stop=next((f for f in features if f.pose=='THREE'),None)
        if stop:
            self.motion.reset();self.pair.reset();self.fist.reset()
            if not active:
                self._hold_key=None;self._hold_since=None;self._hold_fired=False
                return Recognition(hand_ids=(stop.hand_id,),candidate='제어 대기 · V로 시작하세요')
            return self._hold(('THREE',stop.hand_id),at,350,Gesture.STOP,'숫자 3 · 중단 준비')
        if len(features)==1 and features[0].pose=='V' and not active:
            return self._hold(('V',features[0].hand_id),at,600,Gesture.START,'V · 시작 준비')
        if active and len(features)==1 and features[0].pose=='THUMB':
            self.motion.reset();self.pair.reset();self.fist.reset()
            return self._hold(('THUMB',features[0].hand_id),at,600,Gesture.THUMB,'엄지 · 북마크 준비')
        self._hold_key=None;self._hold_since=None;self._hold_fired=False
        if active and len(features)==2:
            self.motion.reset();self.fist.reset()
            gesture,progress,reason=self.pair.update(features,frame.hands,frame.image_width,frame.image_height,at)
            labels={'L_FRAME':'양손 L · 캡처 준비','PINCH_BASELINE':'양손 집기 · 기준 잡기','PINCH_ZOOM':'양손을 벌리거나 모으세요','RELEASE_REQUIRED':'양손 집기를 풀어주세요'}
            return Recognition(gesture,tuple(f.hand_id for f in features),all(f.pose=='OPEN' for f in features),labels.get(reason,'두 손 인식 중'),progress,reason)
        self.pair.reset()
        if active and len(features)==1:
            gesture=self.fist.update(features[0],at,ready)
            if gesture:
                self.motion.reset();return Recognition(gesture,(features[0].hand_id,),False,'주먹 → 펼침 확정',1)
            if features[0].pose in ('INDEX','V'):
                gesture,progress,reason=self.motion.update(features[0],at,frame.image_width,frame.image_height)
                label='검지를 좌우로 쓸거나 원을 그리세요' if features[0].pose=='INDEX' else 'V를 좌우 또는 위아래로 쓸어주세요'
                if reason=='MOTION_READY':label='검지 인식됨 · 좌우로 움직이세요' if features[0].pose=='INDEX' else 'V 인식됨 · 움직일 준비'
                if reason=='MOTION_TOO_SLOW':label='손을 펼친 뒤 조금 더 빠르게 쓸어주세요'
                if reason=='RELEASE_REQUIRED':label='자세를 풀고 다시 동작하세요'
                return Recognition(gesture,(features[0].hand_id,),False,label,progress,reason)
        else:self.fist.reset()
        self.motion.reset()
        ids=tuple(f.hand_id for f in features)
        # Rearm only with the explicit open-palm release shown in the UI.
        # A fist is part of G13 and often a return movement after a swipe;
        # treating it as neutral can restore tabs or arm an unintended reverse.
        neutral=all(f.pose=='OPEN' for f in features)
        names={'V':'V 자세','OPEN':'펼친 손 · 자세 해제','FIST':'주먹 · 준비하려면 손을 펼치세요','UNKNOWN':'손가락을 분명히 보여주세요','THUMB':'엄지 자세','L':'L 자세'}
        label=names.get(features[0].pose,'손동작 준비') if len(features)==1 else '두 손 인식 중'
        if len(features)==1 and features[0].pose=='UNKNOWN':
            f=features[0]
            if f.palm_size<20:label='손 전체를 카메라에 조금 더 가까이 보여주세요'
            elif f.fingers[1]==FingerState.UNKNOWN:label='검지를 끝까지 펴고 손바닥을 카메라 쪽으로 보여주세요'
            elif f.fingers[0]==FingerState.UNKNOWN:label='엄지를 손바닥 쪽으로 조금 접어주세요'
            else:
                unclear=[name for name,state in zip(('중지','약지','새끼손가락'),f.fingers[2:]) if state==FingerState.UNKNOWN]
                label='·'.join(unclear)+': 조금 더 접어주세요' if unclear else '나머지 손가락을 접어 자세를 분명히 해주세요'
        return Recognition(hand_ids=ids,neutral=neutral,candidate=label,reason='UNKNOWN_POSE' if any(f.pose=='UNKNOWN' for f in features) else '')
