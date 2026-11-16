from dataclasses import dataclass
import math
from .features import describe_hand,TimeEMA,distance
from .models import Gesture


@dataclass(frozen=True,slots=True)
class Recognition:
    gesture: Gesture | None = None
    hand_ids: tuple[str,...] = ()
    neutral: bool = False
    candidate: str = '손동작 대기'
    progress: float = 0.0
    reason: str = ''


class GestureRecognizer:
    def __init__(self):
        self.epoch=None;self.last_at=None
        self.reset()

    def reset(self):
        self._hold_key=None;self._hold_since=None;self._hold_fired=False
        self._motion_key=None;self._motion_since=None;self._path=[];self._motion_fired=False
        self._ema=TimeEMA(60);self._curved=False

    def _hold(self,key,at,ms,gesture,label):
        if key!=self._hold_key:
            self._hold_key=key;self._hold_since=at;self._hold_fired=False
        progress=min(1,(at-self._hold_since)/ms)
        event=None
        if progress>=1 and not self._hold_fired:
            event=gesture;self._hold_fired=True
        return Recognition(event,(key[1],),False,label,progress)

    def process(self,frame,active):
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
            if not active:return Recognition(hand_ids=(stop.hand_id,),candidate='제어 대기 · V로 시작하세요')
            return self._hold(('THREE',stop.hand_id),at,350,Gesture.STOP,'숫자 3 · 중단 준비')
        if len(features)==1 and features[0].pose=='V' and not active:
            return self._hold(('V',features[0].hand_id),at,600,Gesture.START,'V · 시작 준비')
        self._hold_key=None;self._hold_since=None;self._hold_fired=False
        if len(features)==1 and features[0].pose=='INDEX' and active:
            return self._swipe(features[0],at)
        self._motion_key=None;self._motion_since=None;self._path=[];self._motion_fired=False;self._ema.reset();self._curved=False
        ids=tuple(f.hand_id for f in features)
        neutral=all(f.pose in ('OPEN','FIST','OTHER') for f in features)
        names={'V':'V 자세','OPEN':'펼친 손 · 자세 해제','FIST':'주먹 · 자세 해제','UNKNOWN':'손가락을 분명히 보여주세요','THUMB':'엄지 자세','L':'L 자세'}
        label=names.get(features[0].pose,'손동작 준비') if len(features)==1 else '두 손 인식 중'
        return Recognition(hand_ids=ids,neutral=neutral,candidate=label,reason='UNKNOWN_POSE' if any(f.pose=='UNKNOWN' for f in features) else '')

    def _swipe(self,feature,at):
        key=(feature.hand_id,feature.pose)
        if key!=self._motion_key:
            self._motion_key=key;self._motion_since=at;self._path=[];self._motion_fired=False;self._ema.reset();self._curved=False
        point=self._ema.update(feature.pointer,at)
        self._path.append((at,point))
        self._path=self._path[-120:]
        if self._motion_fired:return Recognition(hand_ids=(feature.hand_id,),candidate='자세를 풀고 다시 동작하세요',reason='RELEASE_REQUIRED')
        elapsed=at-self._motion_since
        start=self._path[0][1]
        dx,dy=point[0]-start[0],point[1]-start[1]
        length=sum(distance(a[1],b[1]) for a,b in zip(self._path,self._path[1:]))
        straight=math.hypot(dx,dy)/length if length>1e-9 else 0
        if length>.03 and straight<.90:self._curved=True
        if elapsed>600:
            self._motion_fired=True
            return Recognition(hand_ids=(feature.hand_id,),candidate='조금 더 빠르게 쓸어주세요',reason='SWIPE_TOO_SLOW')
        progress=min(1,abs(dx)/.15)
        if elapsed>=150 and abs(dx)>=.15 and abs(dx)>=1.8*abs(dy) and straight>=.90 and not self._curved:
            self._motion_fired=True
            gesture=Gesture.LEFT if dx<0 else Gesture.RIGHT
            return Recognition(gesture,(feature.hand_id,),False,'왼쪽 쓸기 확정' if dx<0 else '오른쪽 쓸기 확정',1)
        return Recognition(hand_ids=(feature.hand_id,),candidate='검지를 좌우로 쓸어주세요',progress=progress,reason='CURVED_PATH' if self._curved else 'SWIPE_IN_PROGRESS')
