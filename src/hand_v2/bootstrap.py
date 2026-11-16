from dataclasses import dataclass,field

from hand_v2.application.controller import Controller
from hand_v2.domain.models import ExecutionMode
from hand_v2.adapters.fakes import FakeForeground, RecordingKeyboard, RecordingUi, ScriptedKeyboard
from hand_v2.adapters.timing import MonotonicClock, Scheduler, SequenceIds


@dataclass
class Runtime:
    controller: Controller
    clock: object
    scheduler: Scheduler
    ids: SequenceIds
    keyboard: object
    foreground: object
    ui: RecordingUi
    camera: object = None
    vision: object = None
    preview_listener: object = None
    camera_wanted: bool = False
    camera_index: int = 0
    preview_enabled: bool = True
    camera_retries: int = 0
    retry_at: int | None = None
    frame_times: list = field(default_factory=list)
    camera_fps: float = 0.0

    def pump(self):
        if hasattr(self.keyboard, 'drain'):
            for kind,payload in self.keyboard.drain():
                if kind=='command':
                    result,action,state=payload
                    self.controller.on_keyboard_state(state)
                    self.controller.on_execution_result(result,action)
                else:
                    result,state=payload
                    self.controller.on_keyboard_state(state)
                    self.controller.on_release_result(result)
        if self.camera:
            for kind,payload in self.camera.poll():
                if kind=='frame':
                    frame=payload.frame
                    if frame.camera_epoch!=self.controller.state.camera_epoch:continue
                    if not 0<=self.clock.now_ms()-frame.captured_at_ms<=250:continue
                    if self.controller.state.camera_status!='CONNECTED':self.controller.camera_connected(frame.camera_epoch)
                    self.vision.accept(frame)
                    self.controller.flush_executor()
                    self.frame_times.append(frame.captured_at_ms)
                    self.frame_times=[t for t in self.frame_times if frame.captured_at_ms-t<=1000]
                    self.camera_fps=(len(self.frame_times)-1)*1000/max(1,self.frame_times[-1]-self.frame_times[0])
                    if payload.preview_rgb and self.preview_enabled and self.preview_listener:self.preview_listener(payload)
                elif kind=='error':
                    self.controller.camera_failed(payload)
                    self.camera_fps=0
                    if self.camera_wanted and self.camera_retries<3 and self.retry_at is None:self.retry_at=self.clock.now_ms()+1000
            if (self.camera_wanted and self.retry_at is not None and self.clock.now_ms()>=self.retry_at
                    and self.camera.session is None):
                self.camera_retries+=1;self.retry_at=None
                self._start_camera()

    def _start_camera(self):
        try:
            if not self.camera.start(self.camera_index,self.preview_enabled):return False
            self.controller.begin_camera(self.camera.epoch)
            self.frame_times=[];self.camera_fps=0
            return True
        except Exception:
            self.controller.camera_failed('CAMERA_START_FAILED')
            self.camera_wanted=False
            return False

    def start_camera(self,index=0,preview=True):
        if self.camera is None:return False
        self.camera_index=index;self.preview_enabled=preview;self.camera_wanted=True;self.camera_retries=0;self.retry_at=None
        return self._start_camera()

    def stop_camera(self):
        self.camera_wanted=False;self.retry_at=None
        if self.camera:self.camera.stop()
        self.camera_fps=0
        self.controller.camera_failed('CAMERA_OFF')

    def set_preview(self,enabled):
        self.preview_enabled=enabled
        if self.camera:self.camera.set_preview(enabled)

    def close(self):
        if self.camera and self.camera.session is not None:return False
        closed = self.keyboard.close() if hasattr(self.keyboard,'close') else True
        # The worker can acknowledge release while close() waits for its thread.
        # Deliver that acknowledgement before publishing the final app state.
        self.pump()
        return closed


def build_runtime(mode=ExecutionMode.SIMULATED, clock=None, initialize=True):
    mode = ExecutionMode(mode)
    clock = clock or MonotonicClock()
    scheduler, ids, ui = Scheduler(clock), SequenceIds(), RecordingUi()
    if mode == ExecutionMode.REAL:
        from hand_v2.adapters.windows.native import Win32
        from hand_v2.adapters.windows.foreground import WindowsForeground
        from hand_v2.adapters.windows.keyboard import WindowsKeyboard
        from hand_v2.adapters.keyboard_worker import KeyboardWorker
        native=Win32()
        foreground=WindowsForeground(clock,native)
        keyboard=KeyboardWorker(WindowsKeyboard(clock,foreground,native),clock)
    elif mode == ExecutionMode.SIMULATED:
        foreground = FakeForeground(clock)
        foreground.set_chrome()
        keyboard = RecordingKeyboard(clock)
    else:
        foreground = FakeForeground(clock)
        keyboard = ScriptedKeyboard(clock)
    controller = Controller(clock, scheduler, ids, keyboard, foreground, ui, mode)
    runtime = Runtime(controller, clock, scheduler, ids, keyboard, foreground, ui)
    from hand_v2.application.vision_control import VisionControl
    from hand_v2.domain.recognition import GestureRecognizer
    runtime.vision=VisionControl(controller,GestureRecognizer())
    if mode==ExecutionMode.REAL:
        from hand_v2.adapters.vision.supervisor import CameraSupervisor
        runtime.camera=CameraSupervisor(clock)
    if initialize:
        controller.initialize(camera_ready=(mode == ExecutionMode.SIMULATED))
    return runtime
