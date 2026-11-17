"""M08 integration review: capture STOP and dialog/image keyboard boundaries."""
from PySide6.QtCore import Qt
from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.qt.window import MainWindow
from hand_v2.adapters.timing import ManualClock
from hand_v2.domain.models import Mode,Activation
from hand_v2.domain.images import ImageAsset
from hand_v2.domain.capture import Display
from tests.hand_samples import sample_frame


def test_numeric_three_cancels_ui_capture_even_when_started_waiting():
    clock=ManualClock(1000);r=build_runtime(clock=clock)
    r.controller.begin_camera(1);r.controller.camera_connected(1)
    r.workspace.request_capture();s=r.workspace.open_capture(Display('screen',0,0,800,600,1))
    assert r.controller.state.activation==Activation.WAITING
    for at in range(1000,1401,50):
        clock.advance_to(at);r.vision.accept(sample_frame(at,'THREE'));r.workspace.tick()
    assert s.closed and r.controller.state.mode==Mode.BROWSER
    assert r.controller.state.last_stop_reason=='숫자 3'


def test_dialog_open_and_close_invalidate_old_recognition_context():
    r=build_runtime();c=r.controller;old=c.state.context_version
    c.set_dialog_lock(True);opened=c.state.context_version
    c.set_dialog_lock(False)
    assert old<opened<c.state.context_version


def test_mode_button_then_arrow_changes_image_without_extra_click(qtbot):
    r=build_runtime();w=MainWindow(r);qtbot.addWidget(w);w.show();w.activateWindow();qtbot.wait(10)
    r.workspace.gallery.replace([ImageAsset(str(i),2,2,bytes([0,100,200,255])*4) for i in range(2)])
    qtbot.mouseClick(w.mode_buttons[Mode.IMAGE],Qt.MouseButton.LeftButton);w._tick()
    from PySide6.QtWidgets import QApplication
    focus=QApplication.focusWidget()
    assert focus is not None
    qtbot.keyClick(focus,Qt.Key.Key_Right)
    assert r.workspace.gallery.index==1
    assert 'Chrome' not in w.target_label.text()
    assert r.keyboard.sent_chords==[]


def test_closing_does_not_reenter_practice(qtbot):
    r=build_runtime();w=MainWindow(r);qtbot.addWidget(w);w.select_page('practice');w._tick()
    w.close()
    assert not w._practice_requested and r.practice_runtime is None
