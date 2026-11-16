from hand_v2.domain.models import ForegroundSnapshot, KeyboardState, ReleaseResult, Result, Status


class FakeForeground:
    def __init__(self, clock):
        self.clock = clock
        self.current = ForegroundSnapshot(clock.now_ms())

    def set_chrome(self, hwnd=10):
        self.current = ForegroundSnapshot(self.clock.now_ms(), hwnd, 100, 1234, "C:/Chrome/chrome.exe", "OK")

    def set_other(self, hwnd=20):
        self.current = ForegroundSnapshot(self.clock.now_ms(), hwnd, 200, 5678, "C:/Windows/notepad.exe", "OK")

    def snapshot(self):
        from dataclasses import replace
        return replace(self.current, observed_at_ms=self.clock.now_ms())


class RecordingKeyboard:
    def __init__(self, clock, auto_release=True):
        self.clock = clock
        self.auto_release = auto_release
        self.sent_chords = []
        self.release_requests = []
        self.state = KeyboardState()
        self.next_status = Status.SENT

    def submit_chord(self, command, chord):
        status = self.next_status
        self.next_status = Status.SENT
        if status == Status.SENT:
            self.sent_chords.append(chord)
        self.state = KeyboardState(self.state.revision+1, self.clock.now_ms(), (), "IDLE")
        return Result(command.command_id, command.context_version, self.clock.now_ms(), status,
                      "SIMULATED" if status == Status.SENT else "INJECTED_FAILURE"), self.state

    def release_owned_keys(self, request_id, context_version):
        self.release_requests.append(request_id)
        if not self.auto_release:
            return None
        self.state = KeyboardState(self.state.revision+1, self.clock.now_ms(), (), "CONFIRMED", request_id)
        return ReleaseResult(request_id, True, self.clock.now_ms()), self.state


class RecordingUi:
    def __init__(self):
        self.states = []
        self.listener = None

    def render_state(self, state):
        self.states.append(state)
        if len(self.states) > 1000:
            del self.states[:500]
        if self.listener:
            self.listener(state)


class ScriptedKeyboard(RecordingKeyboard):
    """Replay requires explicit outcomes; never invent success or release ACK."""
    def __init__(self, clock):
        super().__init__(clock, auto_release=False)
        self.outcomes = []

    def submit_chord(self, command, chord):
        if not self.outcomes:
            return Result(command.command_id, command.context_version, self.clock.now_ms(), Status.BLOCKED, "NO_SCRIPTED_RESULT"), self.state
        outcome = self.outcomes.pop(0)
        if outcome["command_id"] != command.command_id:
            raise ValueError("replay command identity mismatch")
        status = Status(outcome["status"])
        self.state = KeyboardState(**outcome["keyboard_state"])
        if status == Status.SENT:
            self.sent_chords.append(chord)
        return Result(command.command_id, command.context_version, self.clock.now_ms(), status, outcome.get("reason", "")), self.state
