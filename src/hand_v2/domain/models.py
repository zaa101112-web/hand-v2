from dataclasses import dataclass
from enum import StrEnum
import math


def natural(value, name="value"):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def identifier(value):
    if not isinstance(value, str) or not value:
        raise ValueError("nonempty identifier required")


class Mode(StrEnum):
    BROWSER = "BROWSER"
    IMAGE = "IMAGE"
    CAPTURE = "CAPTURE"


class Activation(StrEnum):
    WAITING = "WAITING"
    ACTIVE = "ACTIVE"


class ExecutionMode(StrEnum):
    REAL = "WINDOWS_REAL"
    SIMULATED = "DEV_SIMULATED"
    REPLAY = "REPLAY"


class Gesture(StrEnum):
    START = "G01"
    STOP = "G02"
    LEFT = "G03"
    RIGHT = "G04"
    TAB_LEFT = "G05"
    TAB_RIGHT = "G06"
    PAGE_UP = "G07"
    PAGE_DOWN = "G08"
    ZOOM_IN = "G09"
    ZOOM_OUT = "G10"
    CIRCLE = "G11"
    THUMB = "G12"
    FIST_OPEN = "G13"
    FRAME = "G14"


class Action(StrEnum):
    ACTIVATE = "ACTIVATE"
    STOP = "STOP"
    BACK = "BACK"
    FORWARD = "FORWARD"
    PREV_TAB = "PREV_TAB"
    NEXT_TAB = "NEXT_TAB"
    PAGE_UP = "PAGE_UP"
    PAGE_DOWN = "PAGE_DOWN"
    ZOOM_IN = "ZOOM_IN"
    ZOOM_OUT = "ZOOM_OUT"
    RELOAD = "RELOAD"
    BOOKMARK = "OPEN_BOOKMARK_DIALOG"
    REOPEN_TAB = "REOPEN_TAB"
    PREV_IMAGE = "PREV_IMAGE"
    NEXT_IMAGE = "NEXT_IMAGE"
    FIT_IMAGE = "FIT_IMAGE"
    CAPTURE = "START_CAPTURE"


class Status(StrEnum):
    SENT = "SENT"
    APPLIED = "APPLIED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0

    def __post_init__(self):
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (self.x, self.y, self.z)):
            raise ValueError("landmarks must be finite numbers")


@dataclass(frozen=True, slots=True)
class Hand:
    hand_id: str
    handedness: str
    landmarks: tuple[Landmark, ...]
    raw_handedness: str = "UNKNOWN"
    handedness_score: float | None = None

    def __post_init__(self):
        identifier(self.hand_id)
        if self.handedness not in ("LEFT", "RIGHT", "UNKNOWN"):
            raise ValueError("invalid handedness")
        if type(self.landmarks) is not tuple or len(self.landmarks) != 21 or not all(isinstance(p, Landmark) for p in self.landmarks):
            raise ValueError("exactly 21 immutable landmarks required")
        if self.handedness_score is not None and (not math.isfinite(self.handedness_score) or not 0 <= self.handedness_score <= 1):
            raise ValueError("invalid handedness score")


@dataclass(frozen=True, slots=True)
class TrackingFrame:
    frame_id: int
    captured_at_ms: int
    camera_epoch: int
    image_width: int
    image_height: int
    hands: tuple[Hand, ...]
    schema_name: str = "hand-v2"
    schema_version: int = 1

    def __post_init__(self):
        for name in ("frame_id", "captured_at_ms", "camera_epoch", "image_width", "image_height"):
            natural(getattr(self, name), name)
        if not self.image_width or not self.image_height:
            raise ValueError("positive image dimensions required")
        if type(self.hands) is not tuple or len(self.hands) > 2 or not all(isinstance(h, Hand) for h in self.hands):
            raise ValueError("immutable tuple of at most two hands required")
        if len({h.hand_id for h in self.hands}) != len(self.hands):
            raise ValueError("duplicate hand IDs")
        if self.schema_name != "hand-v2" or type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported tracking schema")


@dataclass(frozen=True, slots=True)
class GestureEvent:
    event_id: str
    gesture: Gesture
    hand_ids: tuple[str, ...]
    captured_at_ms: int
    emitted_at_ms: int
    context_version: int
    camera_epoch: int = 0

    def __post_init__(self):
        identifier(self.event_id)
        if not isinstance(self.gesture, Gesture):
            raise ValueError("unknown gesture")
        if type(self.hand_ids) is not tuple or not 1 <= len(self.hand_ids) <= 2 or len(set(self.hand_ids)) != len(self.hand_ids):
            raise ValueError("one or two distinct hand IDs required")
        for h in self.hand_ids:
            identifier(h)
        for name in ("captured_at_ms", "emitted_at_ms", "context_version", "camera_epoch"):
            natural(getattr(self, name), name)
        if self.emitted_at_ms < self.captured_at_ms:
            raise ValueError("event cannot precede capture")


@dataclass(frozen=True, slots=True)
class ForegroundSnapshot:
    observed_at_ms: int
    hwnd: int = 0
    pid: int = 0
    process_start_time: int = 0
    executable_path: str = ""
    query_status: str = "UNKNOWN"

    def __post_init__(self):
        for name in ("observed_at_ms", "hwnd", "pid", "process_start_time"):
            natural(getattr(self,name),name)
        if self.query_status not in ("OK","UNKNOWN","FAILED") or not isinstance(self.executable_path,str):
            raise ValueError("invalid foreground query")
        if self.query_status == "OK" and (not self.hwnd or not self.pid or not self.executable_path):
            raise ValueError("successful query requires a complete target")

    @property
    def is_chrome(self):
        return self.query_status == "OK" and self.hwnd > 0 and self.pid > 0 and self.executable_path.replace("\\", "/").rsplit("/", 1)[-1].casefold() == "chrome.exe"

    @property
    def identity(self):
        return (self.hwnd, self.pid, self.process_start_time, self.executable_path.casefold())


@dataclass(frozen=True, slots=True)
class Command:
    command_id: str
    source_event_id: str
    action: Action
    target: str
    context_version: int
    issued_at_ms: int
    deadline_ms: int
    target_snapshot: ForegroundSnapshot | None = None

    def __post_init__(self):
        identifier(self.command_id)
        identifier(self.source_event_id)
        if not isinstance(self.action, Action) or self.target not in ("APP","CHROME"):
            raise ValueError("invalid action or target")
        for name in ("context_version","issued_at_ms","deadline_ms"):
            natural(getattr(self,name),name)
        if self.deadline_ms < self.issued_at_ms:
            raise ValueError("command already expired at issue")
        app_actions = {Action.ACTIVATE,Action.STOP,Action.PREV_IMAGE,Action.NEXT_IMAGE,Action.FIT_IMAGE,Action.CAPTURE,Action.ZOOM_IN,Action.ZOOM_OUT}
        if self.target == "APP" and (self.action not in app_actions or self.target_snapshot is not None):
            raise ValueError("invalid internal action")
        if self.target == "CHROME" and (not isinstance(self.target_snapshot,ForegroundSnapshot) or not self.target_snapshot.is_chrome or self.action in app_actions - {Action.ZOOM_IN,Action.ZOOM_OUT}):
            raise ValueError("Chrome shortcut requires an approved target")


@dataclass(frozen=True, slots=True)
class Result:
    command_id: str
    context_version: int
    completed_at_ms: int
    status: Status
    reason: str = ""
    detail: str = ""

    def __post_init__(self):
        identifier(self.command_id)
        natural(self.context_version)
        natural(self.completed_at_ms)
        if not isinstance(self.status,Status):
            raise ValueError("unknown result status")


@dataclass(frozen=True, slots=True)
class KeyboardState:
    revision: int = 0
    observed_at_ms: int = 0
    owned_keys: tuple[str, ...] = ()
    release_status: str = "IDLE"
    release_request_id: str | None = None

    def __post_init__(self):
        natural(self.revision)
        natural(self.observed_at_ms)
        if type(self.owned_keys) is not tuple or len(set(self.owned_keys)) != len(self.owned_keys):
            raise ValueError("immutable unique owned keys required")
        for key in self.owned_keys:
            identifier(key)
        if self.release_status not in ("IDLE","PENDING","CONFIRMED","FAILED"):
            raise ValueError("unknown release status")
        if self.release_status in ("PENDING","CONFIRMED","FAILED"):
            identifier(self.release_request_id)


@dataclass(frozen=True, slots=True)
class ReleaseResult:
    request_id: str
    success: bool
    completed_at_ms: int

    def __post_init__(self):
        identifier(self.request_id)
        natural(self.completed_at_ms)
        if type(self.success) is not bool:
            raise ValueError("boolean release success required")


@dataclass(frozen=True, slots=True)
class AppState:
    revision: int = 0
    context_version: int = 0
    mode: Mode = Mode.BROWSER
    phase: str = "STARTING"
    activation: Activation = Activation.WAITING
    ready: bool = False
    execution_mode: ExecutionMode = ExecutionMode.SIMULATED
    camera_status: str = "DISCONNECTED"
    camera_epoch: int = 0
    blocked_reasons: frozenset[str] = frozenset({"STARTUP_NOT_READY"})
    confirmation_pending: bool = False
    release_pending: bool = False
    keyboard_state: KeyboardState = KeyboardState()
    dialog_lock: bool = False
    last_stop_reason: str = ""
    last_stop_at_ms: int | None = None
    last_candidate: str = "손동작 대기"
    last_execution: Result | None = None
    visible_hand_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.mode,Mode) or not isinstance(self.activation,Activation) or not isinstance(self.execution_mode,ExecutionMode):
            raise ValueError("unknown application enum")
        for name in ("revision","context_version","camera_epoch"):
            natural(getattr(self,name),name)
        if type(self.blocked_reasons) is not frozenset or type(self.visible_hand_ids) is not tuple:
            raise ValueError("application collections must be immutable")
        if not isinstance(self.keyboard_state,KeyboardState):
            raise ValueError("keyboard state required")
