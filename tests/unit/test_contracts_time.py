from dataclasses import FrozenInstanceError
import math

import pytest

from hand_v2.domain.models import Landmark, Hand, TrackingFrame, GestureEvent, Gesture
from hand_v2.adapters.timing import ManualClock, Scheduler, SequenceIds


def hand(id="hand-1"):
    return Hand(id, "UNKNOWN", tuple(Landmark(.5, .5, 0) for _ in range(21)))


def test_contracts_are_immutable_and_nested_collections_are_tuples():
    frame = TrackingFrame(1, 100, 1, 640, 480, (hand(),))
    with pytest.raises(FrozenInstanceError):
        frame.frame_id = 2
    with pytest.raises(ValueError):
        TrackingFrame(1, 100, 1, 640, 480, [hand()])


@pytest.mark.parametrize("x", [math.nan, math.inf, -math.inf])
def test_nonfinite_coordinates_are_rejected(x):
    with pytest.raises(ValueError):
        Landmark(x, .5, 0)


def test_missing_landmarks_duplicate_ids_and_old_schema_are_rejected():
    with pytest.raises(ValueError):
        Hand("a", "LEFT", ())
    with pytest.raises(ValueError):
        TrackingFrame(1, 100, 1, 640, 480, (hand(), hand()))
    with pytest.raises(ValueError):
        TrackingFrame(1, 100, 1, 640, 480, (), schema_version=3)
    with pytest.raises(ValueError):
        TrackingFrame(True, 100, 1, 640, 480, ())


def test_gesture_contract_rejects_future_capture_relative_to_emission():
    with pytest.raises(ValueError):
        GestureEvent("e1", Gesture.LEFT, ("a",), 200, 100, 0)


def test_timers_same_time_fifo_cancel_and_immediate_scheduling():
    clock = ManualClock(0)
    scheduler = Scheduler(clock)
    seen = []
    def first():
        seen.append(("first", clock.now_ms()))
        scheduler.call_at(100, lambda: seen.append(("immediate", clock.now_ms())))
    scheduler.call_at(100, first)
    cancelled = scheduler.call_at(80, lambda: seen.append(("cancelled", 80)))
    scheduler.call_at(100, lambda: seen.append(("second", clock.now_ms())))
    scheduler.cancel(cancelled)
    scheduler.advance_to(100)
    seen.append(("input", clock.now_ms()))
    scheduler.call_at(250, lambda: seen.append(("timeout", clock.now_ms())))
    scheduler.advance_to(300)
    assert seen == [("first", 100), ("second", 100), ("immediate", 100), ("input", 100), ("timeout", 250)]
    assert clock.now_ms() == 300
    with pytest.raises(ValueError):
        scheduler.advance_to(299)


def test_ids_are_reproducible_and_unique():
    a, b = SequenceIds(), SequenceIds()
    assert [a.next_id("event") for _ in range(3)] == [b.next_id("event") for _ in range(3)]
    assert a.next_id("command") != b.next_id("event")


def test_command_and_keyboard_contracts_reject_unsafe_payloads():
    from hand_v2.domain.models import Command, Action, KeyboardState, AppState, ReleaseResult, Result, Status
    with pytest.raises(ValueError):
        Command("c","e","arbitrary-key","CHROME",0,0,250)
    with pytest.raises(ValueError):
        Command("c","e",Action.BACK,"OTHER",0,0,250)
    with pytest.raises(ValueError):
        Command("c","e",Action.BACK,"CHROME",0,0,250)
    with pytest.raises(ValueError):
        KeyboardState(1,0,["CTRL"])
    with pytest.raises(ValueError):
        KeyboardState(1,0,(),"invented")
    with pytest.raises(ValueError):
        AppState(blocked_reasons={"CAMERA_UNAVAILABLE"})
    with pytest.raises(ValueError):
        ReleaseResult("r",1,0)
    with pytest.raises(ValueError):
        Result("c",0,0,"SUCCESS")


def test_action_target_and_deadline_contract():
    from hand_v2.domain.models import Command, Action, ForegroundSnapshot
    snapshot=ForegroundSnapshot(0,10,100,1234,"C:/Chrome/chrome.exe","OK")
    with pytest.raises(ValueError):
        Command("c","e",Action.BACK,"APP",0,0,250)
    with pytest.raises(ValueError):
        Command("c","e",Action.BACK,"CHROME",0,251,250,snapshot)
