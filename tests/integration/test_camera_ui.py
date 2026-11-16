from PySide6.QtCore import Qt,QPoint
from hand_v2.adapters.qt.window import MainWindow
from hand_v2.bootstrap import build_runtime
from hand_v2.domain.models import ExecutionMode


class FakeCamera:
    def __init__(self):self.session=None;self.epoch=0;self.status='STOPPED';self.last_stop=None;self.preview=True;self.events=[]
    def start(self,index=0,preview=True):self.session=object();self.epoch+=1;self.preview=preview;self.status='STARTING';return True
    def stop(self):self.session=None;self.status='STOPPED'
    def poll(self):result=self.events;self.events=[];return result
    def set_preview(self,value):self.preview=value


def test_camera_controls_start_and_stop_without_blocking_ui(qtbot):
    runtime=build_runtime();runtime.camera=FakeCamera()
    window=MainWindow(runtime);qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    qtbot.mouseClick(window.camera_button,Qt.MouseButton.LeftButton)
    assert runtime.camera.session is not None
    assert runtime.controller.state.camera_status=='CONNECTING'
    assert runtime.controller.state.camera_epoch==1
    qtbot.mouseClick(window.preview_checkbox,Qt.MouseButton.LeftButton,pos=QPoint(8,window.preview_checkbox.height()//2))
    assert not runtime.camera.preview
    qtbot.mouseClick(window.camera_button,Qt.MouseButton.LeftButton)
    assert runtime.camera.session is None
    assert runtime.controller.state.camera_status=='DISCONNECTED'


def test_real_window_does_not_expose_simulated_gesture_buttons(qtbot):
    runtime=build_runtime(ExecutionMode.REAL)
    window=MainWindow(runtime);qtbot.addWidget(window)
    assert window.start_button.isHidden()
    assert window.camera_button.text()=='카메라 켜기'
    window.close()
    assert runtime.close()
