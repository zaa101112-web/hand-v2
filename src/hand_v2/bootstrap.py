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
    workspace: object = None
    image_loader: object = None
    capture_worker: object = None
    capture_folder: object = None
    settings: object = None
    config_store: object = None
    practice_runtime: object = None
    practice_progress: object = None
    restart_camera: bool = False
    events: object = None
    calibration: object = None
    last_camera_log: int = 0
    shutdown_guard: object = None

    def emergency_cleanup(self):
        # Called only after the normal close deadline is about to expire. No Qt calls.
        details={'status':'FORCED','exit_code':2,'keys_confirmed':False,'file_completion':'UNCONFIRMED'}
        if self.config_store:
            from hand_v2.adapters.shutdown import write_shutdown_report
            from hand_v2.adapters.configuration import user_data_dir
            write_shutdown_report(user_data_dir(),details)
        try:
            self.keyboard.release_owned_keys('watchdog-shutdown',self.controller.state.context_version)
            if hasattr(self.keyboard,'wait_idle'):self.keyboard.wait_idle(.1)
        except Exception:pass
        try:
            if self.camera and self.camera.session:
                session=self.camera.session;session.request_stop()
                if session.is_alive():session.terminate()
                if session.is_alive():session.kill()
        except Exception:pass
        try:
            if self.capture_worker and self.capture_worker.busy:self.capture_worker.abort()
        except Exception:pass

    def enter_practice(self):
        if self.practice_runtime:return True
        if self.controller.state.mode.value=='CAPTURE':return False
        self.workspace.practice=True
        if self.controller.state.activation.value!='WAITING':self.controller.stop('연습 시작')
        if self.controller.state.release_pending:return False
        self.practice_runtime=build_runtime(ExecutionMode.SIMULATED,clock=self.clock,settings=self.settings)
        from hand_v2.application.practice import PracticeProgress,PracticeActions
        self.practice_progress=PracticeProgress()
        from hand_v2.domain.calibration import Calibration
        self.calibration=Calibration()
        p=self.practice_runtime
        p.workspace.practice=True
        p.controller.app_actions=PracticeActions(self.clock)
        p.controller.begin_camera(self.controller.state.camera_epoch)
        if self.controller.state.camera_status=='CONNECTED':p.controller.camera_connected(self.controller.state.camera_epoch)
        return True

    def stop(self,reason):
        self.controller.stop(reason)
        if self.practice_runtime:self.practice_runtime.controller.stop(reason)
        if self.calibration:self.calibration.cancel()

    def exit_practice(self):
        if self.practice_runtime:
            self.practice_runtime.controller.stop('연습 종료');self.practice_runtime.close()
            self.practice_runtime=None
        if self.calibration:self.calibration.cancel()
        self.workspace.practice=False
        self.controller.stop('연습 종료')

    def apply_settings(self,settings):
        from hand_v2.domain.configuration import validate_config
        from hand_v2.domain.recognition import GestureRecognizer
        value=validate_config(settings)
        camera_changed=self.camera_index!=value['camera']['index']
        wanted=self.camera_wanted
        if camera_changed and self.camera:
            self.stop_camera();self.restart_camera=wanted
        self.settings=value;self.camera_index=value['camera']['index']
        if self.events and hasattr(self.events,'level'):self.events.level=value['logging']['level']
        self.set_preview(value['display']['preview'])
        if self.capture_worker:
            from hand_v2.adapters.screen_capture import default_capture_folder
            self.capture_folder=value['capture']['folder'] or default_capture_folder()
        self.vision.recognizer=GestureRecognizer(value['gestures'])
        self.controller.settings_changed()
        if self.practice_runtime:self.practice_runtime.apply_settings(value)

    def pump(self):
        if self.workspace:self.workspace.tick()
        if self.practice_runtime:
            self.practice_runtime.scheduler.run_due();self.practice_runtime.controller.tick()
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
                    active=self.practice_runtime or self
                    if active is not self:
                        if active.controller.state.camera_epoch!=frame.camera_epoch:active.controller.begin_camera(frame.camera_epoch)
                        active.controller.camera_connected(frame.camera_epoch)
                    active.vision.accept(frame)
                    active.controller.flush_executor()
                    if self.practice_progress and active is not self:self.practice_progress.observe(active.vision.last_recognition,active.controller.state)
                    if self.calibration and active is not self:self.calibration.accept(frame)
                    self.frame_times.append(frame.captured_at_ms)
                    self.frame_times=[t for t in self.frame_times if frame.captured_at_ms-t<=1000]
                    self.camera_fps=(len(self.frame_times)-1)*1000/max(1,self.frame_times[-1]-self.frame_times[0])
                    if self.events and self.clock.now_ms()-self.last_camera_log>=1000:
                        self.last_camera_log=self.clock.now_ms()
                        self.events.record('camera',frame_id=frame.frame_id,epoch=frame.camera_epoch,
                                           frame_age_ms=self.clock.now_ms()-frame.captured_at_ms,fps=self.camera_fps)
                    if payload.preview_rgb and self.preview_enabled and self.preview_listener:self.preview_listener(payload)
                elif kind=='error':
                    self.controller.camera_failed(payload)
                    if self.practice_runtime:self.practice_runtime.controller.camera_failed(payload)
                    self.camera_fps=0
                    if self.camera_wanted and self.camera_retries<3 and self.retry_at is None:self.retry_at=self.clock.now_ms()+1000
            if (self.camera_wanted and self.retry_at is not None and self.clock.now_ms()>=self.retry_at
                    and self.camera.session is None):
                self.camera_retries+=1;self.retry_at=None
                self._start_camera()
            if self.restart_camera and self.camera.session is None:
                self.restart_camera=False;self.start_camera(self.camera_index,self.preview_enabled)
        if self.frame_times and self.clock.now_ms()-self.frame_times[-1]>1000:self.camera_fps=0.

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
        self.camera_wanted=False;self.retry_at=None;self.restart_camera=False
        if self.camera:self.camera.stop()
        self.camera_fps=0
        self.controller.camera_failed('CAMERA_OFF')
        if self.practice_runtime:self.practice_runtime.controller.camera_failed('CAMERA_OFF')
        if self.calibration:self.calibration.cancel()

    def set_preview(self,enabled):
        self.preview_enabled=enabled
        if self.camera:self.camera.set_preview(enabled)

    def close(self):
        if self.image_loader:self.image_loader.close()
        if self.camera and self.camera.session is not None:return False
        closed = self.keyboard.close() if hasattr(self.keyboard,'close') else True
        # The worker can acknowledge release while close() waits for its thread.
        # Deliver that acknowledgement before publishing the final app state.
        self.pump()
        if self.events and hasattr(self.events,'close'):closed=self.events.close() and closed
        if self.shutdown_guard:
            self.shutdown_guard.cancel();closed=closed and not self.shutdown_guard.triggered
        return closed


def build_runtime(mode=ExecutionMode.SIMULATED, clock=None, initialize=True,settings=None,config_store=None,events=None):
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
    if events is None and mode==ExecutionMode.REAL and config_store is not None:
        from hand_v2.adapters.configuration import user_data_dir
        from hand_v2.adapters.event_log import JsonlEvents
        events=JsonlEvents(user_data_dir()/'logs',level=(settings or {}) .get('logging',{}).get('level','INFO'))
    controller = Controller(clock, scheduler, ids, keyboard, foreground, ui, mode,events=events)
    runtime = Runtime(controller, clock, scheduler, ids, keyboard, foreground, ui)
    runtime.events=controller.events
    from hand_v2.adapters.configuration import read_defaults
    from hand_v2.domain.configuration import validate_config
    runtime.settings=validate_config(settings or read_defaults());runtime.config_store=config_store
    runtime.camera_index=runtime.settings['camera']['index'];runtime.preview_enabled=runtime.settings['display']['preview']
    from hand_v2.application.workspace import DesktopWorkspace
    runtime.workspace=DesktopWorkspace(controller,clock,ids)
    controller.app_actions=runtime.workspace
    from hand_v2.adapters.jobs import LatestJob
    from hand_v2.adapters.image_files import load_images
    runtime.image_loader=LatestJob(load_images)
    if mode==ExecutionMode.REAL:
        from hand_v2.adapters.screen_capture import CaptureWorker,default_capture_folder
        runtime.capture_worker=CaptureWorker()
        runtime.capture_folder=runtime.settings['capture']['folder'] or default_capture_folder()
        from hand_v2.adapters.shutdown import ShutdownWatchdog
        runtime.shutdown_guard=ShutdownWatchdog(runtime.emergency_cleanup)
    from hand_v2.application.vision_control import VisionControl
    from hand_v2.domain.recognition import GestureRecognizer
    runtime.vision=VisionControl(controller,GestureRecognizer(runtime.settings['gestures']))
    if mode==ExecutionMode.REAL:
        from hand_v2.adapters.vision.supervisor import CameraSupervisor
        runtime.camera=CameraSupervisor(clock)
    if initialize:
        controller.initialize(camera_ready=(mode == ExecutionMode.SIMULATED))
    return runtime
