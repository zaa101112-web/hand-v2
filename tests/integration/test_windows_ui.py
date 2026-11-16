from PySide6.QtCore import Qt

from hand_v2.adapters.qt.mini_panel import MiniPanel
from hand_v2.adapters.windows.hotkey import GlobalStopHotkey
from hand_v2.bootstrap import build_runtime
from hand_v2.domain.models import ExecutionMode, Activation


class FakeHotkeys:
    def __init__(self, success): self.success, self.calls = success, []
    def register(self, *args): self.calls.append(('register',args)); return self.success
    def unregister(self, *args): self.calls.append(('unregister',args)); return True


def test_f8_conflict_has_no_success_status_or_unregister():
    api=FakeHotkeys(False)
    hotkey=GlobalStopHotkey(123, lambda:None, api)
    assert not hotkey.registered
    hotkey.close()
    assert len(api.calls)==1


def test_f8_registered_once_stops_once_per_message_and_unregisters():
    api=FakeHotkeys(True)
    stops=[]
    hotkey=GlobalStopHotkey(123, lambda:stops.append('F8'), api)
    assert hotkey.registered
    assert not hotkey.dispatch(0x312,999)
    assert hotkey.dispatch(0x312,hotkey.ID)
    assert stops==['F8']
    hotkey.close(); hotkey.close()
    assert len(api.calls)==2


def test_mini_panel_is_no_activate_and_stop_preserves_recent_command(qtbot):
    runtime=build_runtime()
    panel=MiniPanel(runtime.controller,lambda:None)
    qtbot.addWidget(panel)
    assert panel.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert panel.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
    runtime.controller.activate()
    panel.render_state(runtime.controller.state)
    qtbot.mouseClick(panel.stop_button,Qt.MouseButton.LeftButton)
    assert runtime.controller.state.activation==Activation.WAITING
    assert runtime.controller.state.last_stop_reason=='작은 상태창 중단'


def test_real_composition_has_worker_and_stays_waiting_without_camera():
    runtime=build_runtime(ExecutionMode.REAL)
    try:
        assert runtime.controller.state.activation==Activation.WAITING
        assert 'CAMERA_UNAVAILABLE' in runtime.controller.state.blocked_reasons
        assert runtime.keyboard.wait_idle(2)
        runtime.pump()
        assert not runtime.controller.state.release_pending
        assert not runtime.controller.activate()
        assert runtime.foreground.__class__.__name__=='WindowsForeground'
    finally:
        assert runtime.close()
