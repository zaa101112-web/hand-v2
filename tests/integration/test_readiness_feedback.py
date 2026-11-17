from dataclasses import replace

from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.qt.window import MainWindow
from hand_v2.adapters.timing import ManualClock


def test_main_and_overlay_distinguish_release_from_ready_and_confirmation(qtbot):
    runtime=build_runtime(clock=ManualClock(1000))
    window=MainWindow(runtime);qtbot.addWidget(window)
    runtime.controller.activate()
    for label in (window.state_label,window.mini_panel.status):
        assert '손' in label.text() and '펼' in label.text()
        assert '동작 가능' not in label.text()
    runtime.controller.neutral(True)
    runtime.scheduler.advance_to(1180)
    for label in (window.state_label,window.mini_panel.status):
        assert '동작 가능' in label.text()
    state=replace(runtime.controller.state,ready=False,confirmation_pending=True)
    window.render_state(state)
    for label in (window.state_label,window.mini_panel.status):
        assert '계속' in label.text()
        assert '펼' not in label.text()
    state=replace(state,confirmation_pending=False,blocked_reasons=frozenset({'INPUT_RELEASE_FAILED'}))
    window.render_state(state)
    for label in (window.state_label,window.mini_panel.status):
        assert '보류' in label.text()
        assert '동작 가능' not in label.text()
