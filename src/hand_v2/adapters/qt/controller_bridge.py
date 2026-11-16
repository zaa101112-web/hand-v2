from PySide6.QtCore import QObject, Signal


class ControllerBridge(QObject):
    state_changed = Signal(object)

    def render_state(self, state):
        self.state_changed.emit(state)
