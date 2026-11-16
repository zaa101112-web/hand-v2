from .models import Action, Gesture, Mode

_BROWSER = {
    Gesture.LEFT: Action.BACK, Gesture.RIGHT: Action.FORWARD,
    Gesture.TAB_LEFT: Action.PREV_TAB, Gesture.TAB_RIGHT: Action.NEXT_TAB,
    Gesture.PAGE_UP: Action.PAGE_UP, Gesture.PAGE_DOWN: Action.PAGE_DOWN,
    Gesture.ZOOM_IN: Action.ZOOM_IN, Gesture.ZOOM_OUT: Action.ZOOM_OUT,
    Gesture.CIRCLE: Action.RELOAD, Gesture.THUMB: Action.BOOKMARK,
    Gesture.FIST_OPEN: Action.REOPEN_TAB,
}
_IMAGE = {
    Gesture.LEFT: Action.PREV_IMAGE, Gesture.RIGHT: Action.NEXT_IMAGE,
    Gesture.ZOOM_IN: Action.ZOOM_IN, Gesture.ZOOM_OUT: Action.ZOOM_OUT,
    Gesture.FIST_OPEN: Action.FIT_IMAGE,
}
_CHORDS = {
    Action.BACK: ("ALT", "LEFT"), Action.FORWARD: ("ALT", "RIGHT"),
    Action.PREV_TAB: ("CTRL", "SHIFT", "TAB"), Action.NEXT_TAB: ("CTRL", "TAB"),
    Action.PAGE_UP: ("PAGEUP",), Action.PAGE_DOWN: ("PAGEDOWN",),
    Action.ZOOM_IN: ("CTRL", "ADD"), Action.ZOOM_OUT: ("CTRL", "SUBTRACT"),
    Action.RELOAD: ("CTRL", "R"), Action.BOOKMARK: ("CTRL", "D"),
    Action.REOPEN_TAB: ("CTRL", "SHIFT", "T"),
}


def action_for(mode, gesture):
    if gesture == Gesture.STOP:
        return Action.STOP
    if mode == Mode.CAPTURE:
        return None
    if gesture == Gesture.START:
        return Action.ACTIVATE
    if gesture == Gesture.FRAME:
        return Action.CAPTURE
    return (_BROWSER if mode == Mode.BROWSER else _IMAGE).get(gesture)


def chord_for(action):
    return _CHORDS[action]


def target_for(mode, action):
    return "CHROME" if mode == Mode.BROWSER and action not in (Action.ACTIVATE, Action.STOP, Action.CAPTURE) else "APP"
