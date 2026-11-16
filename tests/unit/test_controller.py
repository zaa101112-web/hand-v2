import pytest

from hand_v2.application.controller import Controller
from hand_v2.domain.models import (Action, Activation, ExecutionMode, Gesture, GestureEvent,
                                   KeyboardState, Mode, ReleaseResult, Status)
from hand_v2.domain.mapping import action_for, chord_for
from hand_v2.adapters.fakes import FakeForeground, RecordingKeyboard, RecordingUi
from hand_v2.adapters.timing import ManualClock, Scheduler, SequenceIds


def make_app(auto_release=True, execution_mode=ExecutionMode.SIMULATED):
    clock = ManualClock(1000)
    scheduler = Scheduler(clock)
    ids = SequenceIds()
    keyboard = RecordingKeyboard(clock, auto_release=auto_release)
    foreground = FakeForeground(clock)
    if execution_mode != ExecutionMode.REPLAY:
        foreground.set_chrome()
    ui = RecordingUi()
    app = Controller(clock, scheduler, ids, keyboard, foreground, ui, execution_mode)
    app.initialize(camera_ready=True)
    return app, clock, scheduler, keyboard, foreground


def event(app, clock, gesture=Gesture.LEFT, id="e1", age=0, **kwargs):
    return GestureEvent(id, gesture, ("hand-1",), clock.now_ms()-age, clock.now_ms(), kwargs.get("context", app.state.context_version), app.state.camera_epoch)


def arm(app, clock, scheduler):
    app.activate()
    app.neutral(True)
    scheduler.advance_to(clock.now_ms()+180)


def test_waiting_then_fresh_neutral_required():
    app, clock, scheduler, keyboard, fg = make_app()
    assert app.state.mode == Mode.BROWSER
    assert app.state.activation == Activation.WAITING
    app.activate()
    app.handle(event(app, clock))
    app.flush_executor()
    assert keyboard.sent_chords == []
    app.neutral(True)
    scheduler.advance_to(1179)
    assert not app.state.ready
    scheduler.advance_to(1180)
    assert app.state.ready
    app.handle(event(app, clock, id="fresh"))
    app.flush_executor()
    assert keyboard.sent_chords == [("ALT", "LEFT")]


@pytest.mark.parametrize("age,expected", [(249,1),(250,1),(251,0)])
def test_event_age_boundary(age, expected):
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    app.handle(event(app, clock, age=age))
    app.flush_executor()
    assert len(keyboard.sent_chords) == expected


def test_target_changes_between_approval_and_execution():
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    app.handle(event(app, clock))
    fg.set_other()
    app.flush_executor()
    assert keyboard.sent_chords == []
    assert app.state.last_execution.reason == "TARGET_CHANGED"
    assert app.state.activation == Activation.ACTIVE
    fg.set_chrome()
    app.refresh_target()
    assert not app.state.ready


def test_nonchrome_input_is_not_queued_for_later():
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    fg.set_other()
    app.handle(event(app, clock))
    fg.set_chrome()
    app.flush_executor()
    assert not keyboard.sent_chords


def test_duplicate_and_outdated_context_do_not_send():
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    ev = event(app, clock)
    app.handle(ev)
    app.flush_executor()
    app.neutral(True)
    scheduler.advance_to(clock.now_ms()+600)
    app.handle(ev)
    app.handle(event(app, clock, id="old", context=999))
    app.flush_executor()
    assert len(keyboard.sent_chords) == 1


def test_stop_cancels_queued_input_and_preserves_last_result_through_cleanup():
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    app.handle(event(app, clock))
    app.stop("F8")
    result = app.state.last_execution
    app.flush_executor()
    assert keyboard.sent_chords == []
    assert app.state.activation == Activation.WAITING
    assert app.state.last_stop_reason == "F8"
    assert app.state.last_execution == result
    assert not app.state.release_pending


def test_matching_result_and_latest_empty_keyboard_state_both_required():
    app, clock, scheduler, keyboard, fg = make_app(auto_release=False)
    request = keyboard.release_requests[-1]
    app.on_release_result(ReleaseResult("wrong", True, clock.now_ms()))
    app.on_keyboard_state(KeyboardState(1, clock.now_ms(), (), "CONFIRMED", request))
    assert app.state.release_pending
    app.activate()
    assert app.state.activation == Activation.WAITING
    app.on_release_result(ReleaseResult(request, True, clock.now_ms()))
    assert not app.state.release_pending
    app.activate()
    assert app.state.activation == Activation.ACTIVE
    app.stop("button")
    new = keyboard.release_requests[-1]
    app.on_keyboard_state(KeyboardState(2, clock.now_ms(), ("CTRL",), "CONFIRMED", new))
    app.on_release_result(ReleaseResult(new, True, clock.now_ms()))
    assert app.state.release_pending
    app.on_keyboard_state(KeyboardState(1, clock.now_ms(), (), "CONFIRMED", new))
    assert app.state.release_pending
    app.on_keyboard_state(KeyboardState(3, clock.now_ms(), (), "CONFIRMED", new))
    assert not app.state.release_pending


def test_release_failure_and_multiple_block_recovery():
    app, clock, scheduler, keyboard, fg = make_app(auto_release=False)
    req = keyboard.release_requests[-1]
    app.on_release_result(ReleaseResult(req, False, clock.now_ms()))
    app.block("CAMERA_UNAVAILABLE")
    app.recover("CAMERA_UNAVAILABLE")
    assert "INPUT_RELEASE_FAILED" in app.state.blocked_reasons
    app.activate()
    assert app.state.activation == Activation.WAITING


def test_mode_switch_and_hand_loss_keep_activation_but_require_rearm():
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    app.set_mode(Mode.IMAGE)
    assert app.state.activation == Activation.ACTIVE
    assert not app.state.ready
    app.neutral(True)
    scheduler.advance_to(clock.now_ms()+180)
    app.hands_lost()
    assert app.state.activation == Activation.ACTIVE
    assert not app.state.ready


def test_bookmark_requires_explicit_continue_not_elapsed_time():
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    app.handle(event(app, clock, Gesture.THUMB))
    app.flush_executor()
    assert app.state.confirmation_pending
    app.neutral(True)
    scheduler.advance_to(clock.now_ms()+5000)
    app.handle(event(app, clock, id="other"))
    app.flush_executor()
    assert len(keyboard.sent_chords) == 1
    app.ack_confirmation()
    assert not app.state.ready
    app.neutral(True)
    scheduler.advance_to(clock.now_ms()+180)
    app.handle(event(app, clock, id="after-ack"))
    app.flush_executor()
    assert len(keyboard.sent_chords) == 2


def test_internal_action_does_not_send_os_keys_or_claim_unimplemented_success():
    app, clock, scheduler, keyboard, fg = make_app()
    arm(app, clock, scheduler)
    app.set_mode(Mode.IMAGE)
    app.neutral(True)
    scheduler.advance_to(clock.now_ms()+180)
    app.handle(event(app, clock))
    app.flush_executor()
    assert not keyboard.sent_chords
    assert app.state.last_execution.reason == "NOT_IMPLEMENTED"


def test_replay_does_not_invent_release_ack():
    app, clock, scheduler, keyboard, fg = make_app(False, ExecutionMode.REPLAY)
    assert app.state.release_pending
    assert app.state.activation == Activation.WAITING


@pytest.mark.parametrize("gesture,action,chord", [
    (Gesture.LEFT,Action.BACK,("ALT","LEFT")),(Gesture.RIGHT,Action.FORWARD,("ALT","RIGHT")),
    (Gesture.TAB_LEFT,Action.PREV_TAB,("CTRL","SHIFT","TAB")),(Gesture.TAB_RIGHT,Action.NEXT_TAB,("CTRL","TAB")),
    (Gesture.PAGE_UP,Action.PAGE_UP,("PAGEUP",)),(Gesture.PAGE_DOWN,Action.PAGE_DOWN,("PAGEDOWN",)),
    (Gesture.ZOOM_IN,Action.ZOOM_IN,("CTRL","ADD")),(Gesture.ZOOM_OUT,Action.ZOOM_OUT,("CTRL","SUBTRACT")),
    (Gesture.CIRCLE,Action.RELOAD,("CTRL","R")),(Gesture.THUMB,Action.BOOKMARK,("CTRL","D")),
    (Gesture.FIST_OPEN,Action.REOPEN_TAB,("CTRL","SHIFT","T"))])
def test_browser_mapping(gesture,action,chord):
    assert action_for(Mode.BROWSER,gesture) == action
    assert chord_for(action) == chord


@pytest.mark.parametrize("gesture,action", [(Gesture.LEFT,Action.PREV_IMAGE),(Gesture.RIGHT,Action.NEXT_IMAGE),
    (Gesture.ZOOM_IN,Action.ZOOM_IN),(Gesture.ZOOM_OUT,Action.ZOOM_OUT),(Gesture.FIST_OPEN,Action.FIT_IMAGE)])
def test_image_mapping(gesture,action):
    assert action_for(Mode.IMAGE,gesture) == action


@pytest.mark.parametrize("mode", list(Mode))
def test_shared_start_stop_and_capture_mode_policy(mode):
    assert action_for(mode,Gesture.STOP) == Action.STOP
    if mode != Mode.CAPTURE:
        assert action_for(mode,Gesture.START) == Action.ACTIVATE
        assert action_for(mode,Gesture.FRAME) == Action.CAPTURE
    else:
        assert action_for(mode,Gesture.START) is None
        assert action_for(mode,Gesture.LEFT) is None


@pytest.mark.parametrize("g", [Gesture.TAB_LEFT,Gesture.TAB_RIGHT,Gesture.PAGE_UP,Gesture.PAGE_DOWN,Gesture.CIRCLE,Gesture.THUMB])
def test_unbound_image_gestures(g):
    assert action_for(Mode.IMAGE,g) is None
