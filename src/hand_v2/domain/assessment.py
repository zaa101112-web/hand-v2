"""Fixed prompted trials. Pure scoring; camera/keyboard/file effects live outside."""
from dataclasses import dataclass
from .models import Gesture


@dataclass(frozen=True, slots=True)
class Trial:
    label: str
    gesture: Gesture
    count: int = 1


CONTINUOUS_TRIALS = (
    Trial('검지 왼쪽 → 뒤로가기',Gesture.LEFT),
    Trial('검지 오른쪽 → 앞으로가기',Gesture.RIGHT),
    Trial('V 왼쪽 → 이전 탭',Gesture.TAB_LEFT),
    Trial('V 오른쪽 → 다음 탭',Gesture.TAB_RIGHT),
    Trial('V 아래 → 페이지 아래',Gesture.PAGE_DOWN),
    Trial('V 위 → 페이지 위',Gesture.PAGE_UP),
    Trial('양손 집기 유지 → 간격 벌려 확대 2단계',Gesture.ZOOM_IN,2),
    Trial('양손 집기 유지 → 간격 좁혀 축소 2단계',Gesture.ZOOM_OUT,2),
)


class ContinuousAssessment:
    def __init__(self,source,trials=CONTINUOUS_TRIALS,trial_ms=5000,warmup_ms=3000):
        if not trials or trial_ms<=0 or warmup_ms<0 or any(t.count<1 for t in trials):
            raise ValueError('positive trial durations/counts required')
        self.source=source;self.trials=tuple(trials);self.trial_ms=trial_ms;self.warmup_ms=warmup_ms
        self.started=None;self.now=0;self.invalid_reason='';self.observed=[]

    def start(self,at):
        self.started=at;self.now=at;self.invalid_reason='';self.observed=[]

    @property
    def end(self):
        return self.started+self.warmup_ms+len(self.trials)*self.trial_ms if self.started is not None else 0

    @property
    def active(self):
        return self.started is not None and not self.invalid_reason and self.now<self.end

    def tick(self,at):
        if self.active:self.now=max(self.now,at)

    def invalidate(self,reason):
        if self.active:self.invalid_reason=reason

    def observe(self,at,gesture,executed):
        # The UI clock normally leads camera capture time by a few milliseconds.
        # Score by capture time, without accepting events outside the schedule.
        if self.started is None or self.invalid_reason or not self.started<=at<self.end:return
        if self.observed and at<self.observed[-1][1]:return
        self.tick(at)
        index=(at-self.started-self.warmup_ms)//self.trial_ms
        if index<0:return
        if len(self.observed)>=1000:self.invalidate('EVENT_LIMIT');return
        self.observed.append((index,at,gesture,bool(executed)))

    def prompt(self):
        if self.invalid_reason:return '측정 무효: '+self.invalid_reason+' · 다시 시작하세요'
        if self.started is None:return '연속 동작 8과제 / 10단계 · 과제당 5초'
        if self.now>=self.end:return '측정 완료 · 아래 결과를 확인하세요'
        elapsed=self.now-self.started-self.warmup_ms
        if elapsed<0:return '준비 · V를 0.6초 유지해 시작하고 잠깐 멈추세요'
        index=elapsed//self.trial_ms
        left=(self.trial_ms-elapsed%self.trial_ms+999)//1000
        return f'{index+1}/{len(self.trials)} · {self.trials[index].label} · 남은 {left}초'

    def report(self):
        rows=[]
        for index,trial in enumerate(self.trials):
            observations=[(at,g,ok) for i,at,g,ok in self.observed if i==index]
            matching=[(at,ok) for at,g,ok in observations if g==trial.gesture]
            rows.append(dict(label=trial.label,gesture=trial.gesture.value,expected=trial.count,
                recognized=min(len(matching),trial.count),missed=max(0,trial.count-len(matching)),
                executed=sum(ok for _,ok in matching[:trial.count]),
                wrong=sum(g!=trial.gesture for _,g,_ in observations),
                duplicates=max(0,len(matching)-trial.count),
                blocked_or_failed=sum(not ok for _,_,ok in observations),
                observations=[dict(at_ms=at,gesture=g.value,executed=ok) for at,g,ok in observations]))
        totals={key:sum(row[key] for row in rows) for key in
                ('expected','recognized','missed','executed','wrong','duplicates','blocked_or_failed')}
        complete=self.started is not None and self.now>=self.end
        valid=self.started is not None and not self.invalid_reason
        measured=complete and valid
        return dict(source=self.source,complete=complete,valid=valid,invalid_reason=self.invalid_reason,
            **totals,recognition_rate=totals['recognized']/totals['expected'] if measured else None,
            execution_rate=totals['executed']/totals['expected'] if measured else None,
            passed=measured and totals['executed']==totals['expected'] and not totals['wrong'] and not totals['duplicates'],
            trials=rows,limitation='Prompted practice with virtual outputs; not real Chrome effects or three-person accuracy.')
