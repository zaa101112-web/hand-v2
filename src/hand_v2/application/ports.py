from typing import Callable, Protocol
from hand_v2.domain.models import AppState, Command, ForegroundSnapshot, KeyboardState, ReleaseResult, Result


class Clock(Protocol):
    def now_ms(self) -> int: ...


class TimerPort(Protocol):
    def call_at(self, at_ms: int, callback: Callable[[], None]) -> int: ...
    def cancel(self, token: int | None) -> None: ...


class IdSource(Protocol):
    def next_id(self, prefix: str = "id") -> str: ...


class ForegroundPort(Protocol):
    def snapshot(self) -> ForegroundSnapshot: ...


class KeyboardPort(Protocol):
    def submit_chord(self, command: Command, chord: tuple[str, ...]) -> tuple[Result, KeyboardState] | None: ...
    def release_owned_keys(self, request_id: str, context_version: int) -> tuple[ReleaseResult, KeyboardState] | None: ...


class UiPort(Protocol):
    def render_state(self, state: AppState) -> None: ...


class AppActionPort(Protocol):
    def execute(self, command: Command) -> Result: ...
class EventSink:
    def record(self,kind,**fields):pass

