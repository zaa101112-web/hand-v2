import math
from statistics import median
from .features import describe_hand,distance


def recommend_swipe(still_ms,noise,left,right):
    if still_ms<5000 or len(left)<10 or len(right)<10:raise ValueError('5초 정지와 좌우 각각 10회 표본이 필요합니다.')
    if not all(math.isfinite(x) and .05<=x<=.8 for x in (*left,*right)):raise ValueError('이동 표본이 올바르지 않습니다.')
    if not math.isfinite(noise) or noise>.03:raise ValueError('정지 중 흔들림이 큽니다. 조명과 카메라 위치를 확인하세요.')
    if min(median(left),median(right))/max(median(left),median(right))<.6:raise ValueError('좌우 이동 거리 차이가 큽니다. 균형 있게 다시 시도하세요.')
    lower=min(sorted(left)[len(left)//10],sorted(right)[len(right)//10])
    if noise*6>=lower:raise ValueError('흔들림과 의도한 이동을 구별할 표본이 부족합니다.')
    return round(min(.25,max(.10,lower*.65,noise*6)),2)


class Calibration:
    def __init__(self):self.phase='IDLE';self.reset_data()
    def reset_data(self):
        self.still=[];self.still_ms=0;self.noise=0.;self.left=[];self.right=[]
        self.path=[];self.armed=False;self.last_at=None;self.hand=None;self.epoch=None
        self.recommendation=None;self.error=''
    def start(self):self.reset_data();self.phase='STILL'
    def cancel(self):self.reset_data();self.phase='IDLE'
    def accept(self,frame):
        if self.epoch is not None and self.epoch!=frame.camera_epoch:self.cancel();self.error='카메라가 바뀌어 추천 측정을 취소했습니다.'
        self.epoch=frame.camera_epoch
        features=tuple(describe_hand(h,frame.image_width,frame.image_height) for h in frame.hands)
        if len(features)==1:
            f=features[0];self.sample(frame.captured_at_ms,f.hand_id,f.pose,f.pointer)
        else:self.sample(frame.captured_at_ms,None,'UNKNOWN',(0,0))
    def sample(self,at,hand,pose,point):
        if self.phase not in ('STILL','LEFT','RIGHT'):return
        discontinuous=(hand!=self.hand or (self.last_at is not None and (at<=self.last_at or at-self.last_at>100)))
        self.hand=hand;self.last_at=at
        if discontinuous:
            self.path=[]
            if self.phase=='STILL':self.still=[];self.still_ms=0
        if self.phase=='STILL':
            if pose!='INDEX':self.still=[];self.still_ms=0;return
            self.still.append((at,point));self.still=self.still[-500:]
            self.still_ms=at-self.still[0][0]
            if self.still_ms>=5000:
                xs=[p[0] for _,p in self.still];ys=[p[1] for _,p in self.still]
                self.noise=math.hypot(max(xs)-min(xs),max(ys)-min(ys))
                if self.noise>.03:self.phase='ERROR';self.error='정지 중 흔들림이 큽니다. 다시 측정하세요.'
                else:self.phase='LEFT';self.armed=False
            return
        if pose=='OPEN':
            if self.path:self._finish_path()
            self.path=[];self.armed=True;return
        if pose!='INDEX':self.path=[];self.armed=False;return
        if self.armed:self.path.append((at,point));self.path=self.path[-100:]
    def _finish_path(self):
        if len(self.path)<3:return
        duration=self.path[-1][0]-self.path[0][0]
        a,b=self.path[0][1],self.path[-1][1];dx,dy=b[0]-a[0],b[1]-a[1]
        length=sum(distance(p,q) for (_,p),(_,q) in zip(self.path,self.path[1:]))
        if not (150<=duration<=600 and .05<=abs(dx)<=.8 and abs(dx)>=1.8*abs(dy) and length>0 and math.hypot(dx,dy)/length>=.9):return
        if self.phase=='LEFT' and dx<0:
            self.left.append(abs(dx))
            if len(self.left)==10:self.phase='RIGHT'
        elif self.phase=='RIGHT' and dx>0:
            self.right.append(abs(dx))
            if len(self.right)==10:
                try:self.recommendation=recommend_swipe(self.still_ms,self.noise,self.left,self.right);self.phase='READY'
                except ValueError as exc:self.phase='ERROR';self.error=str(exc)
