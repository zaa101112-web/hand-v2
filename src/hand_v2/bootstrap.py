from dataclasses import dataclass

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

    def close(self):
        return self.keyboard.close() if hasattr(self.keyboard,'close') else True


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
    if initialize:
        controller.initialize(camera_ready=(mode == ExecutionMode.SIMULATED))
    return runtime
