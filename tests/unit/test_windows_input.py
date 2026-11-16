from dataclasses import replace
import ctypes

import pytest

from hand_v2.adapters.timing import ManualClock
from hand_v2.adapters.fakes import FakeForeground
from hand_v2.adapters.windows.keyboard import WindowsKeyboard, KeyInput, chord_inputs
from hand_v2.adapters.windows.foreground import WindowsForeground
from hand_v2.adapters.windows.native import INPUT, KEYBDINPUT
from hand_v2.domain.models import Action, Command, Status


class FakeNative:
    def __init__(self):
        self.calls = []
        self.counts = []
        self.pressed = set()
        self.current = (10, 100, 1234, 'C:/Chrome/chrome.exe')
        self.fail = False

    def foreground_identity(self):
        if self.fail:
            raise OSError('access denied')
        return self.current

    def is_down(self, vk):
        return vk in self.pressed

    def send(self, inputs):
        self.calls.append(inputs)
        return (self.counts.pop(0) if self.counts else len(inputs), 5)


def rig():
    clock = ManualClock(1000)
    api = FakeNative()
    fg = WindowsForeground(clock, api)
    keyboard = WindowsKeyboard(clock, fg, api)
    cmd = Command('c1', 'e1', Action.BACK, 'CHROME', 0, 1000, 1250, fg.snapshot())
    return clock, api, fg, keyboard, cmd


def test_win64_input_abi_and_extended_keys():
    assert ctypes.sizeof(INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    assert ctypes.sizeof(KEYBDINPUT) == (24 if ctypes.sizeof(ctypes.c_void_p) == 8 else 16)
    batch = chord_inputs(('ALT', 'LEFT'))
    assert [(x.vk, x.flags) for x in batch] == [(0x12, 0), (0x25, 1), (0x25, 3), (0x12, 2)]


def test_full_batch_only_means_sent_not_effect_verified():
    _, api, _, keys, cmd = rig()
    result, state = keys.submit_chord(cmd, ('ALT', 'LEFT'))
    assert result.status == Status.SENT
    assert result.reason == 'OS_INPUT_SENT'
    assert len(api.calls) == 1 and len(api.calls[0]) == 4
    assert not state.owned_keys


@pytest.mark.parametrize('sent', [0, 1, 2, 3])
def test_partial_input_fails_and_releases_only_accepted_owned_downs(sent):
    _, api, _, keys, cmd = rig()
    api.counts = [sent]
    result, state = keys.submit_chord(cmd, ('ALT', 'LEFT'))
    assert result.status == Status.FAILED and result.reason == 'SENDINPUT_PARTIAL'
    assert not state.owned_keys
    if sent:
        assert all(item.flags & 2 for batch in api.calls[1:] for item in batch)
    else:
        assert len(api.calls) == 1


def test_failed_cleanup_is_bounded_and_never_claims_release():
    _, api, _, keys, cmd = rig()
    api.counts = [1, 0, 0]
    result, state = keys.submit_chord(cmd, ('ALT', 'LEFT'))
    assert result.status == Status.FAILED
    assert state.owned_keys == ('ALT',)
    assert len(api.calls) == 3
    api.counts = [0, 0]
    ack, state = keys.release_owned_keys('r1', 1)
    assert not ack.success and state.release_status == 'FAILED'


@pytest.mark.parametrize('vk', [0xA0,0xA1,0xA2,0xA3,0xA4,0xA5,0x5B,0x5C,0x25])
def test_user_held_modifier_or_main_key_blocks_without_release(vk):
    _, api, _, keys, cmd = rig()
    api.pressed.add(vk)
    result, _ = keys.submit_chord(cmd, ('ALT', 'LEFT'))
    assert result.status == Status.BLOCKED and result.reason == 'KEYBOARD_BUSY'
    assert api.calls == []


@pytest.mark.parametrize('kind', ['window', 'pid', 'start', 'path', 'expired', 'unavailable'])
def test_execution_time_target_identity_and_expiry(kind):
    clock, api, _, keys, cmd = rig()
    if kind == 'expired': clock.advance_to(1251)
    elif kind == 'unavailable': api.fail = True
    else:
        values = list(api.current)
        i = ['window','pid','start','path'].index(kind)
        values[i] = 'C:/Other/chrome.exe' if i == 3 else values[i]+1
        api.current = tuple(values)
    result, _ = keys.submit_chord(cmd, ('ALT', 'LEFT'))
    assert result.status == Status.BLOCKED
    assert api.calls == []


def test_callers_cannot_replace_the_trusted_chord():
    _, api, _, keys, cmd = rig()
    result, _ = keys.submit_chord(cmd, ('CTRL', 'R'))
    assert result.status == Status.BLOCKED and result.reason == 'INVALID_CHORD'
    assert not api.calls


def test_foreground_query_failure_never_uses_last_success():
    _, api, fg, _, _ = rig()
    assert fg.snapshot().is_chrome
    api.fail = True
    assert not fg.snapshot().is_chrome
    assert fg.snapshot().query_status == 'FAILED'
