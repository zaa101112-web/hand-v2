from dataclasses import replace
from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.timing import ManualClock
from hand_v2.application.vision_control import VisionControl
from hand_v2.domain.recognition import GestureRecognizer
from hand_v2.domain.models import Activation,TrackingFrame
from tests.hand_samples import sample_frame


def rig():
    runtime=build_runtime(clock=ManualClock(1000))
    runtime.controller.begin_camera(1)
    runtime.controller.camera_connected(1)
    return runtime,VisionControl(runtime.controller,GestureRecognizer())


def feed(runtime,vision,pose,start,end,offset=lambda t:0):
    for at in range(start,end+1,50):
        runtime.scheduler.advance_to(at)
        vision.accept(sample_frame(at,pose,offset(at-start)))
        runtime.controller.flush_executor()


def test_landmarks_start_rearm_swipe_and_stop_reach_controller():
    r,v=rig()
    feed(r,v,'V',1000,1600)
    assert r.controller.state.activation==Activation.ACTIVE and not r.controller.state.ready
    feed(r,v,'OPEN',1650,1850)
    assert r.controller.state.ready
    feed(r,v,'INDEX',1900,2400,lambda t:.24*t/500)
    assert r.keyboard.sent_chords==[('ALT','LEFT')]
    feed(r,v,'THREE',2450,2800)
    assert r.controller.state.activation==Activation.WAITING
    assert not r.controller.state.keyboard_state.owned_keys


def test_loss_is_not_stop_and_reacquired_command_needs_release():
    r,v=rig();feed(r,v,'V',1000,1600);feed(r,v,'OPEN',1650,1850)
    r.scheduler.advance_to(1900);v.accept(TrackingFrame(1900,1900,1,640,480,()))
    assert r.controller.state.activation==Activation.ACTIVE and not r.controller.state.ready
    feed(r,v,'INDEX',1950,2450,lambda t:.24*t/500)
    assert r.keyboard.sent_chords==[]


def test_stale_epoch_or_frame_cannot_affect_activation():
    r,v=rig()
    assert not v.accept(sample_frame(1000,'V',epoch=0))
    r.scheduler.advance_to(1300)
    assert not v.accept(sample_frame(1000,'V'))
    assert r.controller.state.activation==Activation.WAITING


def test_camera_recovery_does_not_clear_unrelated_fault_or_auto_activate():
    r,v=rig();r.controller.block('INPUT_FAILED')
    r.controller.camera_failed('CAMERA_STALLED')
    r.controller.camera_connected(1)
    assert r.controller.state.blocked_reasons==frozenset({'INPUT_FAILED'})
    assert r.controller.state.activation==Activation.WAITING
