from hand_v2.domain.models import Activation,Command,GestureEvent,Mode


class VisionControl:
    """Main-thread use case: validate freshness, recognize, then ask the normal policy."""
    def __init__(self,controller,recognizer):
        self.controller=controller;self.recognizer=recognizer
        self.context=None;self.epoch=None;self.last_frame=-1;self.last_at=-1
        self.last_recognition=None
        self.recognized_events=[]
        self.target_identity=None
        self.last_command=None

    def accept(self,frame):
        self.last_command=None
        core=self.controller;state=core.state;now=core.clock.now_ms()
        if frame.camera_epoch!=state.camera_epoch or not 0<=now-frame.captured_at_ms<=250:
            return False
        if self.epoch!=frame.camera_epoch:
            self.epoch=frame.camera_epoch;self.last_frame=-1;self.last_at=-1;self.recognizer.reset()
        if frame.frame_id<=self.last_frame or frame.captured_at_ms<=self.last_at:return False
        if state.mode==Mode.BROWSER:
            target=core.refresh_target()
            if target.identity!=self.target_identity:
                self.recognizer.reset();core.neutral(False)
                self.target_identity=target.identity
            state=core.state
        self.last_frame=frame.frame_id;self.last_at=frame.captured_at_ms
        if self.context!=state.context_version:
            self.recognizer.reset();self.context=state.context_version
        # UI capture may start while WAITING; numeric-three must still cancel it.
        result=self.recognizer.process(frame,state.activation==Activation.ACTIVE or state.mode==Mode.CAPTURE,ready=state.ready)
        self.last_recognition=result
        if not frame.hands:
            core.hands_lost();return True
        core.show_candidate(result.candidate,tuple(h.hand_id for h in frame.hands))
        core.neutral(result.neutral or result.prepared)
        if result.gesture:
            event=GestureEvent(core.ids.next_id('gesture'),result.gesture,result.hand_ids,
                               frame.captured_at_ms,now,state.context_version,frame.camera_epoch)
            self.recognized_events.append(event)
            self.recognized_events=self.recognized_events[-256:]
            outcome=core.handle(event)
            if isinstance(outcome,Command):self.last_command=outcome
        return True
