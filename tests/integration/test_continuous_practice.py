from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.qt.window import MainWindow
from hand_v2.adapters.timing import ManualClock


def test_practice_assessment_requires_camera_and_demo_invalidates(qtbot):
    r=build_runtime(clock=ManualClock(1000));w=MainWindow(r);qtbot.addWidget(w)
    w.select_page('practice');w._tick();panel=w.practice_panel
    r.controller.camera_failed('CAMERA_OFF')
    panel.start_assessment()
    assert not r.practice_assessment.active
    r.controller.camera_connected(r.controller.state.camera_epoch)
    panel.start_assessment()
    assert r.practice_assessment.active
    panel.example()
    assert r.practice_assessment.report()['invalid_reason']=='DEMO_INPUT'
    assert r.keyboard.sent_chords==[]


def test_assessment_marks_camera_disconnection_and_settings_change_invalid():
    r=build_runtime(clock=ManualClock(1000));r.enter_practice()
    a=r.practice_assessment;a.start(1000);r.stop_camera()
    assert a.report()['invalid_reason']=='CAMERA_OFF'
    a.start(1000);r.apply_settings(r.settings)
    assert a.report()['invalid_reason']=='SETTINGS_CHANGED'


def test_real_runtime_packet_route_scores_once_and_only_virtual_output():
    from hand_v2.adapters.vision.process import VisionPacket
    from tests.continuous_samples import continuous_frames
    class Camera:
        session=None
        pending=[]
        def poll(self):
            packets=self.pending;self.pending=[];return packets
    r=build_runtime(clock=ManualClock(1000));r.controller.begin_camera(1);r.controller.camera_connected(1)
    r.enter_practice();a=r.practice_assessment;a.start(1000);r.camera=Camera()
    for frame in continuous_frames(50):
        r.clock.advance_to(frame.captured_at_ms+10)
        r.camera.pending=[('frame',VisionPacket(frame)),('frame',VisionPacket(frame))]
        r.pump()
    r.clock.advance_to(44000);r.pump()
    assert a.report()['executed']==10 and a.report()['duplicates']==0
    assert r.keyboard.sent_chords==[]
