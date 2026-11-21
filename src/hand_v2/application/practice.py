from hand_v2.domain.models import Gesture,Result,Status


class PracticeProgress:
    TASKS=(('V 시작',Gesture.START),('동작 준비',None),('검지 왼쪽 쓸기',Gesture.LEFT),
           ('검지 오른쪽 쓸기',Gesture.RIGHT),('양손 확대',Gesture.ZOOM_IN),('숫자 3 중단',Gesture.STOP))
    def __init__(self):self.completed=set();self.events=[]
    def observe(self,recognition,state):
        if not recognition:return
        if recognition.gesture:
            self.completed.add(recognition.gesture);self.events.append(recognition.gesture)
            self.events=self.events[-100:]
        if state.ready:self.completed.add(None)


class PracticeActions:
    def __init__(self,clock):self.clock=clock;self.actions=[]
    def execute(self,command):
        self.actions.append(command.action)
        self.actions=self.actions[-100:]
        return Result(command.command_id,command.context_version,self.clock.now_ms(),Status.APPLIED,'PRACTICE_ONLY')
