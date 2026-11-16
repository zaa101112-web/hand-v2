from hand_v2.domain.models import Activation,GestureEvent


class VisionControl:
    """Main-thread use case: validate freshness, recognize, then ask the normal policy."""
    def __init__(self,controller,recognizer):
        self.controller=controller;self.recognizer=recognizer
        self.context=None;self.epoch=None;self.last_frame=-1;self.last_at=-1
        self.last_recognition=None
        self.recognized_events=[]

    def accept(self,frame):
        core=self.controller;state=core.state;now=core.clock.now_ms()
        if frame.camera_epoch!=state.camera_epoch or not 0<=now-frame.captured_at_ms<=250:
            return False
        if self.epoch!=frame.camera_epoch:
            self.epoch=frame.camera_epoch;self.last_frame=-1;self.last_at=-1;self.recognizer.reset()
        if frame.frame_id<=self.last_frame or frame.captured_at_ms<=self.last_at:return False
        self.last_frame=frame.frame_id;self.last_at=frame.captured_at_ms
        if self.context!=state.context_version:
            self.recognizer.reset();self.context=state.context_version
        result=self.recognizer.process(frame,state.activation==Activation.ACTIVE)
        self.last_recognition=result
        if not frame.hands:
            core.hands_lost();return True
        core.show_candidate(result.candidate,tuple(h.hand_id for h in frame.hands))
        core.neutral(result.neutral)
        if result.gesture:
            event=GestureEvent(core.ids.next_id('gesture'),result.gesture,result.hand_ids,
                               frame.captured_at_ms,now,state.context_version,frame.camera_epoch)
            self.recognized_events.append(event)
            self.recognized_events=self.recognized_events[-256:]
            core.handle(event)
        return True
