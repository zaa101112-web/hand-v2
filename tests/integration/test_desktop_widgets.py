from PySide6.QtCore import Qt
from hand_v2.domain.capture import CaptureSession, Display, Rect
from hand_v2.adapters.qt.capture_overlay import CaptureOverlay
from hand_v2.adapters.qt.image_panel import ImagePanel
from hand_v2.bootstrap import build_runtime
from hand_v2.domain.models import Mode
from hand_v2.domain.images import ImageAsset


def test_overlay_physical_keyboard_selection_and_explicit_confirmation(qtbot):
    session=CaptureSession('s',1,'BROWSER',Display('test',0,0,800,600,1.25))
    calls=[]
    overlay=CaptureOverlay(session,lambda:calls.append('save'),lambda:calls.append('cancel'))
    qtbot.addWidget(overlay);overlay.show();overlay.setFocus()
    before=session.rect
    qtbot.keyClick(overlay,Qt.Key.Key_Right,Qt.KeyboardModifier.ShiftModifier)
    assert session.rect.left==before.left+10
    qtbot.keyClick(overlay,Qt.Key.Key_Down,Qt.KeyboardModifier.ControlModifier)
    assert session.rect.bottom==before.bottom+1
    assert calls==[]
    qtbot.keyClick(overlay,Qt.Key.Key_Return)
    assert calls==['save']
    qtbot.keyClick(overlay,Qt.Key.Key_Escape)
    assert calls==['save','cancel']


def test_image_panel_buttons_and_keys_use_same_gallery(qtbot):
    r=build_runtime();r.controller.set_mode(Mode.IMAGE)
    r.workspace.gallery.replace([ImageAsset(str(i),2,2,bytes([200,0,0,255])*4) for i in range(3)])
    panel=ImagePanel(r.workspace,lambda folder:None)
    qtbot.addWidget(panel);panel.show();panel.refresh()
    qtbot.mouseClick(panel.next_button,Qt.MouseButton.LeftButton)
    assert r.workspace.gallery.index==1
    qtbot.keyClick(panel,Qt.Key.Key_Right)
    assert r.workspace.gallery.index==2
    qtbot.keyClick(panel,Qt.Key.Key_Plus)
    assert r.workspace.gallery.scale==1.15
    assert r.keyboard.sent_chords==[]
