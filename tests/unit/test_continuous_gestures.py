"""ADR-15: authored trajectories; never a measurement of human accuracy."""
from dataclasses import replace
import pytest

from hand_v2.domain.models import Activation, Gesture, TrackingFrame
from hand_v2.domain.recognition import GestureRecognizer
from tests.unit.test_vision_control import rig, feed
from tests.unit.test_extended_recognition import zoom_frame
from tests.unit.test_motion_preparation import moved_frame


def deliver(r, v, frames):
    for f in frames:
        r.scheduler.advance_to(f.captured_at_ms)
        v.accept(f)
        r.controller.flush_executor()


@pytest.mark.parametrize('pose,axis,chords',[
    ('INDEX','x',[('ALT','LEFT'),('ALT','RIGHT')]),
    ('V','x',[('CTRL','SHIFT','TAB'),('CTRL','TAB')]),
    ('V','y',[('PAGEDOWN',),('PAGEUP',)]),
])
def test_repeat_motion_without_open_after_stationary_endpoint(pose,axis,chords):
    r,v=rig();feed(r,v,'V',1000,1600)
    def f(at,value):return moved_frame(at,pose,value if axis=='x' else 0,value if axis=='y' else 0)
    frames=[f(t,0) for t in range(1650,2051,50)]
    frames += [f(2050+t,.24*t/500) for t in range(50,501,50)]
    frames += [f(t,.24) for t in range(2600,3551,50)]
    frames += [f(3550+t,.24-.24*t/500) for t in range(50,501,50)]
    frames += [f(t,0) for t in range(4100,6051,50)]
    deliver(r,v,frames)
    assert r.keyboard.sent_chords==chords


def test_held_index_and_immediate_bounce_never_repeat():
    r,v=rig();feed(r,v,'V',1000,1600);feed(r,v,'INDEX',1650,2050)
    feed(r,v,'INDEX',2100,2600,lambda t:.24*t/500)
    feed(r,v,'INDEX',2650,3150,lambda t:.24-.24*t/500)
    feed(r,v,'INDEX',3200,7000)
    assert r.keyboard.sent_chords==[('ALT','LEFT')]


def zoom_sequence(start=1650,interval=20):
    # Holding each new spacing MUST produce exactly one step, even while EMA settles.
    for i,sep in enumerate((.50,.65,.85,.65,.50)):
        for t in range(0,1000,interval):yield zoom_frame(start+i*1000+t,sep)


def test_two_hand_continuous_zoom_reverses_without_unpinching():
    r,v=rig();feed(r,v,'V',1000,1600)
    deliver(r,v,zoom_sequence())
    assert r.keyboard.sent_chords==[('CTRL','ADD')]*2+[('CTRL','SUBTRACT')]*2
    assert r.controller.state.activation==Activation.ACTIVE


def test_smoothing_tail_never_causes_stationary_zoom_or_false_reverse():
    rec=GestureRecognizer();events=[]
    for f in zoom_sequence():
        result=rec.process(f,True)
        if result.gesture:events.append(result.gesture)
    assert events==[Gesture.ZOOM_IN]*2+[Gesture.ZOOM_OUT]*2


def test_zoom_stop_and_one_hand_loss_cancel_old_distance():
    r,v=rig();feed(r,v,'V',1000,1600)
    deliver(r,v,[zoom_frame(t,.50) for t in range(1650,2051,50)])
    deliver(r,v,[zoom_frame(t,.65) for t in range(2100,2551,50)])
    one=zoom_frame(2600,.65)
    deliver(r,v,[replace(one,hands=one.hands[:1])])
    deliver(r,v,[zoom_frame(t,.85) for t in range(2650,3151,50)])
    assert len(r.keyboard.sent_chords)==1
    feed(r,v,'THREE',3200,3550)
    deliver(r,v,[zoom_frame(t,.75) for t in range(3600,4051,50)])
    assert len(r.keyboard.sent_chords)==1
    assert r.controller.state.activation==Activation.WAITING


def test_foreground_switch_discards_partial_zoom():
    r,v=rig();feed(r,v,'V',1000,1600)
    deliver(r,v,[zoom_frame(t,.50) for t in range(1650,2051,50)])
    r.foreground.set_chrome(hwnd=999)
    deliver(r,v,[zoom_frame(t,.85) for t in range(2100,2651,50)])
    assert r.keyboard.sent_chords==[]


def test_dialog_lock_blocks_continuous_zoom():
    r,v=rig();feed(r,v,'V',1000,1600)
    r.controller.set_dialog_lock(True)
    deliver(r,v,zoom_sequence())
    assert r.keyboard.sent_chords==[]


def test_zoom_rate_is_bounded_and_every_chord_releases_keys():
    r,v=rig();feed(r,v,'V',1000,1600)
    deliver(r,v,[zoom_frame(t,.40) for t in range(1650,2051,20)])
    emitted=[]
    for t in range(2070,3271,20):
        deliver(r,v,[zoom_frame(t,.40*2**((t-2050)/650))])
        if len(r.keyboard.sent_chords)>len(emitted):emitted.append(t)
        assert not r.controller.state.keyboard_state.owned_keys
    assert len(emitted)>=3
    assert all(b-a>=200 for a,b in zip(emitted,emitted[1:]))
