from PySide6.QtCore import Qt
from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.qt.window import MainWindow


def test_recommendation_waits_for_explicit_apply(qtbot):
    r=build_runtime();w=MainWindow(r);qtbot.addWidget(w);w.select_page('practice');w._tick()
    c=r.calibration;c.phase='READY';c.recommendation=.12;c.left=[.2]*10;c.right=[.2]*10;c.still_ms=5000
    w.practice_panel.refresh()
    assert r.settings['gestures']['swipe_distance']==.15
    assert '0.15' in w.practice_panel.calibration_info.text() and '0.12' in w.practice_panel.calibration_info.text()
    qtbot.mouseClick(w.practice_panel.apply_recommendation,Qt.MouseButton.LeftButton);w._tick()
    assert r.settings['gestures']['swipe_distance']==.12
