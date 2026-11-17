from dataclasses import replace
import pytest
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


def test_fist_reposition_after_swipe_cannot_rearm_forward_command():
    r,v=rig();feed(r,v,'V',1000,1600);feed(r,v,'OPEN',1650,1850)
    feed(r,v,'INDEX',1900,2400,lambda t:.24*t/500)
    feed(r,v,'FIST',2450,3450)
    assert not r.controller.state.ready
    feed(r,v,'INDEX',3500,4000,lambda t:.24-.24*t/500)
    assert r.keyboard.sent_chords==[('ALT','LEFT')]
    feed(r,v,'OPEN',4050,4300)
    assert r.controller.state.ready


def test_fist_open_during_rearm_does_not_restore_an_unrelated_tab():
    r,v=rig();feed(r,v,'V',1000,1600);feed(r,v,'OPEN',1650,1850)
    feed(r,v,'INDEX',1900,2400,lambda t:.24*t/500)
    feed(r,v,'FIST',2450,3450);feed(r,v,'OPEN',3500,4000)
    assert r.keyboard.sent_chords==[('ALT','LEFT')]
    assert r.controller.state.ready


def test_fist_open_from_ready_still_restores_tab_once():
    r,v=rig();feed(r,v,'V',1000,1600);feed(r,v,'OPEN',1650,1850)
    feed(r,v,'FIST',1900,2250);feed(r,v,'OPEN',2300,2850)
    assert r.keyboard.sent_chords==[('CTRL','SHIFT','T')]


@pytest.mark.parametrize('interval',[40,49,60,64,66,90])
@pytest.mark.parametrize('already_ready',[False,True])
def test_rearm_timer_cannot_make_an_in_progress_fist_open_eligible(interval,already_ready):
    r,v=rig();feed(r,v,'V',1000,1600);feed(r,v,'OPEN',1650,1850)
    if not already_ready:feed(r,v,'INDEX',1900,2400,lambda t:.24*t/500)
    feed(r,v,'FIST',2450,3450)
    for at in range(3500,4201,interval):
        r.scheduler.advance_to(at);v.accept(sample_frame(at,'OPEN'));r.controller.flush_executor()
    expected=[('CTRL','SHIFT','T')] if already_ready else [('ALT','LEFT')]
    assert r.keyboard.sent_chords==expected


def test_three_prepared_swipes_reach_keyboard_after_explicit_open_release():
    from tests.unit.test_motion_preparation import moved_frame
    r,v=rig();feed(r,v,'V',1000,1600);feed(r,v,'OPEN',1650,1850)
    for start in (1900,4400,6900):
        frames=[moved_frame(start+t,'INDEX',dy=-.08*t/150) for t in range(0,151,50)]
        frames += [moved_frame(start+t,'INDEX',dy=-.08) for t in range(200,801,50)]
        frames += [moved_frame(start+800+t,'INDEX',.24*t/500,-.08) for t in range(50,551,50)]
        for f in frames:
            r.scheduler.advance_to(f.captured_at_ms);v.accept(f);r.controller.flush_executor()
        feed(r,v,'OPEN',start+1400,start+2200)
    assert r.keyboard.sent_chords==[('ALT','LEFT')]*3
