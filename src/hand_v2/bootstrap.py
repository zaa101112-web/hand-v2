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


def build_runtime(mode=ExecutionMode.SIMULATED, clock=None, initialize=True):
    mode = ExecutionMode(mode)
    if mode == ExecutionMode.REAL:
        raise RuntimeError("Windows real input is not implemented in M01")
    clock = clock or MonotonicClock()
    scheduler, ids, ui = Scheduler(clock), SequenceIds(), RecordingUi()
    foreground = FakeForeground(clock)
    if mode == ExecutionMode.SIMULATED:
        foreground.set_chrome()
        keyboard = RecordingKeyboard(clock)
    else:
        keyboard = ScriptedKeyboard(clock)
    controller = Controller(clock, scheduler, ids, keyboard, foreground, ui, mode)
    runtime = Runtime(controller, clock, scheduler, ids, keyboard, foreground, ui)
    if initialize:
        controller.initialize(camera_ready=(mode == ExecutionMode.SIMULATED))
    return runtime
