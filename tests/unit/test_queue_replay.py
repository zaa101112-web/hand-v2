from pathlib import Path
import pytest

from hand_v2.adapters.replay import run_fixture
from hand_v2.domain.models import Action, Command, ForegroundSnapshot
from hand_v2.domain.queue import CommandQueue
from hand_v2.bootstrap import build_runtime
from hand_v2.domain.models import ExecutionMode


def test_queue_is_bounded_and_clear_returns_owned_pending_work():
    queue = CommandQueue()
    commands = [Command(str(i),str(i),Action.PREV_IMAGE,"APP",0,0,250) for i in range(9)]
    assert all(queue.offer(c) for c in commands[:8])
    assert not queue.offer(commands[8])
    assert len(queue) == 8
    assert queue.clear() == tuple(commands[:8])
    assert queue.take() is None


def test_control_fixture_has_exact_reproducible_output():
    path = Path(__file__).parents[1] / "fixtures/control/back_once"
    first = run_fixture(path)
    assert first["sent_chords"] == [["ALT", "LEFT"]]
    assert first["activation"] == "WAITING"
    assert first["owned_keys"] == []
    assert first["release_pending"] is False
    assert all(run_fixture(path) == first for _ in range(9))


def test_replay_output_does_not_autofill_success_or_target():
    runtime = build_runtime(ExecutionMode.REPLAY)
    assert not runtime.foreground.snapshot().is_chrome
    assert runtime.controller.state.release_pending
    snapshot=ForegroundSnapshot(0,10,100,1234,"C:/Chrome/chrome.exe","OK")
    cmd = Command("c1","e1",Action.BACK,"CHROME",0,0,250,snapshot)
    result, keys = runtime.keyboard.submit_chord(cmd,("ALT","LEFT"))
    assert result.reason == "NO_SCRIPTED_RESULT"
    assert not runtime.keyboard.sent_chords


def test_unimplemented_real_mode_fails_closed():
    with pytest.raises(RuntimeError, match="not implemented"):
        build_runtime(ExecutionMode.REAL)
