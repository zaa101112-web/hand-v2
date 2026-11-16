from dataclasses import replace
from threading import Event

from hand_v2.adapters.keyboard_worker import KeyboardWorker
from hand_v2.adapters.fakes import RecordingKeyboard
from hand_v2.adapters.timing import ManualClock
from hand_v2.bootstrap import build_runtime
from hand_v2.domain.models import Activation, Action, Command, Status


def test_release_cancels_waiting_work_and_ack_is_not_command_result():
    clock = ManualClock(1000)
    runtime = build_runtime(clock=clock)
    backend = RecordingKeyboard(clock)
    entered, resume = Event(), Event()
    original = backend.submit_chord
    def delayed(command, chord):
        entered.set()
        assert resume.wait(2)
        return original(command, chord)
    backend.submit_chord = delayed
    worker = KeyboardWorker(backend, clock)
    cmd = Command('one', 'event', Action.BACK, 'CHROME', 0, 1000, 1250, runtime.foreground.snapshot())
    try:
        assert worker.submit_chord(cmd, ('ALT','LEFT')) is None
        assert entered.wait(1)
        worker.submit_chord(replace(cmd, command_id='two'), ('ALT','LEFT'))
        assert worker.release_owned_keys('stop-ack', 1) is None
        resume.set()
        assert worker.wait_idle(2)
        messages = worker.drain()
        assert backend.sent_chords == [('ALT','LEFT')]
        assert any(kind=='command' and payload[0].command_id=='two' and payload[0].status==Status.CANCELLED for kind,payload in messages)
        assert any(kind=='release' and payload[0].request_id=='stop-ack' and payload[0].success for kind,payload in messages)
    finally:
        resume.set()
        assert worker.close()


def test_async_results_apply_on_controller_thread_and_old_context_is_ignored():
    runtime = build_runtime(clock=ManualClock(1000))
    c = runtime.controller
    c.activate()
    c.neutral(True)
    runtime.scheduler.advance_to(1180)
    from hand_v2.domain.models import Gesture, GestureEvent, Result
    command = c.handle(GestureEvent('e1',Gesture.THUMB,('h1',),1180,1180,0))
    c.keyboard.submit_chord = lambda *args: None
    c.flush_executor()
    assert c.state.last_execution is None
    c.on_execution_result(Result(command.command_id,0,1180,Status.SENT,'OS_INPUT_SENT'), command.action)
    assert c.state.confirmation_pending
    c.stop('F8')
    previous = c.state.last_execution
    c.on_execution_result(Result('old',0,1180,Status.FAILED,'late'), Action.BACK)
    assert c.state.last_execution == previous
    assert 'INPUT_FAILED' not in c.state.blocked_reasons


def test_worker_exception_produces_failure_and_survives_to_release():
    clock=ManualClock(1000)
    runtime=build_runtime(clock=clock)
    backend=RecordingKeyboard(clock)
    def broken(*args): raise RuntimeError('injected')
    backend.submit_chord=broken
    worker=KeyboardWorker(backend,clock)
    try:
        cmd=Command('one','e1',Action.BACK,'CHROME',0,1000,1250,runtime.foreground.snapshot())
        worker.submit_chord(cmd,('ALT','LEFT'))
        assert worker.wait_idle(2)
        assert worker.drain()[0][1][0].status == Status.FAILED
        worker.release_owned_keys('cleanup',1)
        assert worker.wait_idle(2)
        assert worker.drain()[0][1][0].success
    finally:
        assert worker.close()


def test_shutdown_cannot_report_success_when_release_ack_failed():
    clock=ManualClock(1000)
    backend=RecordingKeyboard(clock)
    def broken(*args): raise OSError('release unavailable')
    backend.release_owned_keys=broken
    worker=KeyboardWorker(backend,clock)
    assert not worker.close()
