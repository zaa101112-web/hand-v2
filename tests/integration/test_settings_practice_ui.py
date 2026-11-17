from PySide6.QtCore import Qt
from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.qt.window import MainWindow
from hand_v2.domain.models import Activation


def test_four_menus_are_functional_and_practice_is_isolated(qtbot):
    r=build_runtime();w=MainWindow(r);qtbot.addWidget(w);w.show()
    w.select_page('practice');w._tick()
    assert r.practice_runtime is not None
    assert '구현 예정' not in w.pages.currentWidget().accessibleDescription()
    assert '실제 키' in w.practice_panel.status.text()
    w.select_page('settings');w._tick()
    assert r.practice_runtime is None and r.controller.state.activation==Activation.WAITING
    w.settings_panel.swipe.setValue(.2)
    qtbot.mouseClick(w.settings_panel.save_button,Qt.MouseButton.LeftButton);w._tick()
    assert r.settings['gestures']['swipe_distance']==.2
    assert r.controller.state.dialog_lock is False
    w.resize(960,640)
    assert w.pages.currentWidget().widgetResizable()
