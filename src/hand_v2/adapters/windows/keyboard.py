from dataclasses import dataclass

from hand_v2.domain.mapping import chord_for
from hand_v2.domain.models import KeyboardState, ReleaseResult, Result, Status

VK = {'CTRL':0x11, 'SHIFT':0x10, 'ALT':0x12, 'TAB':0x09, 'LEFT':0x25, 'RIGHT':0x27,
      'PAGEUP':0x21, 'PAGEDOWN':0x22, 'ADD':0x6B, 'SUBTRACT':0x6D, 'R':0x52, 'D':0x44, 'T':0x54}
EXTENDED = {'LEFT','RIGHT','PAGEUP','PAGEDOWN'}
MODIFIERS = (0x10,0x11,0x12,0xA0,0xA1,0xA2,0xA3,0xA4,0xA5,0x5B,0x5C)


@dataclass(frozen=True, slots=True)
class KeyInput:
    key: str
    vk: int
    flags: int


def key_input(key, up=False):
    return KeyInput(key, VK[key], (1 if key in EXTENDED else 0) | (2 if up else 0))


def chord_inputs(chord):
    return tuple(key_input(k) for k in chord) + tuple(key_input(k, True) for k in reversed(chord))


class WindowsKeyboard:
    """Single worker owns this adapter and all synthetic key ownership."""
    def __init__(self, clock, foreground, native):
        self.clock, self.foreground, self.native = clock, foreground, native
        self.state = KeyboardState()
        self._owned = []
        self.can_send = lambda: True

    def _state(self, status='IDLE', request=None):
        self.state = KeyboardState(self.state.revision+1, self.clock.now_ms(), tuple(self._owned), status, request)
        return self.state

    def _apply_accepted(self, batch, count):
        for key in batch[:count]:
            if key.flags & 2:
                if key.key in self._owned:
                    self._owned.remove(key.key)
            elif key.key not in self._owned:
                self._owned.append(key.key)

    def _release(self):
        for _ in range(2):
            if not self._owned:
                return True
            batch = tuple(key_input(k, True) for k in reversed(self._owned))
            try:
                count, _ = self.native.send(batch)
                self._apply_accepted(batch, count)
            except OSError:
                continue
        return not self._owned

    def release_owned_keys(self, request_id, context_version):
        ok = self._release()
        return (ReleaseResult(request_id, ok, self.clock.now_ms()),
                self._state('CONFIRMED' if ok else 'FAILED', request_id))

    def submit_chord(self, command, chord):
        def reply(status, reason, detail=''):
            return Result(command.command_id, command.context_version, self.clock.now_ms(), status, reason, detail), self._state()
        if command.target != 'CHROME' or chord != chord_for(command.action):
            return reply(Status.BLOCKED, 'INVALID_CHORD')
        if self._owned:
            return reply(Status.BLOCKED, 'OWNED_KEYS_PENDING')
        try:
            if any(self.native.is_down(vk) for vk in {*MODIFIERS, *(VK[k] for k in chord)}):
                return reply(Status.BLOCKED, 'KEYBOARD_BUSY')
            # Check at the boundary, after all preparation and immediately before SendInput.
            batch = chord_inputs(chord)
            current = self.foreground.snapshot()
            if not current.is_chrome or current.identity != command.target_snapshot.identity:
                return reply(Status.BLOCKED, 'TARGET_CHANGED')
            if self.clock.now_ms() > command.deadline_ms:
                return reply(Status.BLOCKED, 'STALE_COMMAND')
            if not self.can_send():
                return reply(Status.CANCELLED, 'RELEASE_REQUESTED')
            count, error = self.native.send(batch)
            self._apply_accepted(batch, count)
            if count == len(batch):
                return reply(Status.SENT, 'OS_INPUT_SENT', f'accepted={count}/{len(batch)}; page effect unverified')
            self._release()
            return reply(Status.FAILED, 'SENDINPUT_PARTIAL', f'accepted={count}/{len(batch)}; last_error={error}; UIPI cause unknown')
        except OSError as error:
            self._release()
            return reply(Status.FAILED, 'NATIVE_INPUT_ERROR', str(error))
