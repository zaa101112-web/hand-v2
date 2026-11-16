import math
from dataclasses import replace

import pytest

from hand_v2.domain.models import Gesture,TrackingFrame
from hand_v2.domain.recognition import GestureRecognizer
from tests.hand_samples import sample_hand,sample_frame


def shifted(hand,dx=0,dy=0,flip=False):
    return replace(hand,landmarks=tuple(replace(p,x=(1-p.x if flip else p.x)+dx,y=(1-p.y if flip else p.y)+dy) for p in hand.landmarks))


def frame(at,*hands):return TrackingFrame(at,at,1,640,480,tuple(hands))
def events(results):return [r.gesture for r in results if r.gesture]


@pytest.mark.parametrize('dx,dy,expected',[(.24,0,Gesture.TAB_LEFT),(-.24,0,Gesture.TAB_RIGHT),(0,-.24,Gesture.PAGE_UP),(0,.24,Gesture.PAGE_DOWN)])
def test_v_axis_swipes_emit_one_command(dx,dy,expected):
    r=GestureRecognizer()
    output=[r.process(frame(1000+t,shifted(sample_hand('V'),dx*t/500,dy*t/500)),True) for t in range(0,1001,50)]
    assert events(output)==[expected]


def test_v_axis_cannot_switch_and_diagonal_is_not_a_command():
    for curved in (False,True):
        r=GestureRecognizer();output=[]
        for t in range(0,601,50):
            dx=.24*t/600 if not curved else min(t/150,1)*.06
            dy=.24*t/600 if not curved else max(0,t-150)/450*.26
            output.append(r.process(frame(1000+t,shifted(sample_hand('V'),dx,dy)),True))
        assert events(output)==[]


@pytest.mark.parametrize('duration,want',[(599,[]),(600,[Gesture.THUMB]),(1200,[Gesture.THUMB])])
def test_thumb_hold_boundary_once(duration,want):
    r=GestureRecognizer()
    result=[r.process(sample_frame(1000+t,'THUMB'),True) for t in list(range(0,duration,50))+[duration]]
    assert events(result)==want


def test_fist_open_requires_both_durations_and_never_stops():
    r=GestureRecognizer()
    assert events([r.process(sample_frame(1000+t,'FIST'),True) for t in range(0,301,50)])==[]
    out=[r.process(sample_frame(1350+t,'OPEN'),True) for t in (0,50,100,149,150,200,500)]
    assert events(out)==[Gesture.FIST_OPEN]


@pytest.mark.parametrize('kind',['short_fist','late_open','hand_change','unknown'])
def test_fist_open_invalid_sequences(kind):
    r=GestureRecognizer()
    duration=200 if kind=='short_fist' else 1500 if kind=='late_open' else 300
    out=[r.process(sample_frame(1000+t,'FIST'),True) for t in range(0,duration+1,50)]
    if kind=='unknown':out.append(r.process(frame(1000+duration+25,sample_hand('L')),True))
    out += [r.process(sample_frame(1050+duration+t,'OPEN',hand_id='h2' if kind=='hand_change' else 'h1'),True) for t in range(0,301,50)]
    assert events(out)==[]


def pinched(hand_id,dx,ratio=.1):
    hand=sample_hand('FIST',hand_id,dx)
    p=list(hand.landmarks);tip=p[8];p[4]=replace(tip,x=tip.x+.24*ratio)
    return replace(hand,landmarks=tuple(p))


def zoom_frame(at,separation=.50,ratio=.1,ids=('left','right')):
    return frame(at,pinched(ids[0],-separation/2,ratio),pinched(ids[1],separation/2,ratio))


@pytest.mark.parametrize('separation,want',[(.70,Gesture.ZOOM_IN),(.38,Gesture.ZOOM_OUT)])
def test_two_hand_zoom_baseline_confirmation_and_hold_once(separation,want):
    r=GestureRecognizer();out=[]
    for t in range(0,201,20):out.append(r.process(zoom_frame(1000+t),True))
    for t in range(220,1001,20):out.append(r.process(zoom_frame(1000+t,separation),True))
    assert events(out)==[want]
    first=next(i for i in out if i.gesture)
    assert len(first.hand_ids)==2


def test_zoom_release_hysteresis_loss_and_id_change():
    r=GestureRecognizer();out=[]
    for t in range(0,201,20):out.append(r.process(zoom_frame(1000+t),True))
    for t in range(220,501,20):out.append(r.process(zoom_frame(1000+t,.70,.36),True))
    assert events(out)==[Gesture.ZOOM_IN]  # Middle band keeps the previous pinch state.
    r.process(frame(1520),True)
    assert r.process(zoom_frame(1540,.90,ids=('new','right')),True).gesture is None
    assert r.process(frame(1560,pinched('only',0)),True).gesture is None


def circle_frames(direction=1,radius=.10,angle=360,duration=1400,phase=0):
    for t in range(0,duration+1,40):
        theta=math.radians(phase)+direction*math.radians(angle)*t/duration
        yield frame(1000+t,shifted(sample_hand('INDEX'),radius*480/640*math.cos(theta),radius*math.sin(theta)))


@pytest.mark.parametrize('direction',[-1,1])
def test_circle_both_directions_excludes_swipe(direction):
    r=GestureRecognizer()
    assert events([r.process(f,True) for f in circle_frames(direction)])==[Gesture.CIRCLE]


@pytest.mark.parametrize('radius,angle',[(.02,360),(.28,360),(.10,250)])
def test_circle_wrong_radius_or_open_path_is_rejected(radius,angle):
    r=GestureRecognizer()
    assert events([r.process(f,True) for f in circle_frames(radius=radius,angle=angle)])==[]


def l_frame(at,pose='L',opposite=True):
    return frame(at,shifted(sample_hand(pose,'left'),-.23),shifted(sample_hand(pose,'right'),.23,flip=opposite))


@pytest.mark.parametrize('duration,want',[(799,[]),(800,[Gesture.FRAME]),(1000,[Gesture.FRAME])])
def test_opposed_l_frame_hold(duration,want):
    r=GestureRecognizer()
    out=[r.process(l_frame(1000+t),True) for t in list(range(0,duration,50))+[duration]]
    assert events(out)==want
    assert all(len(x.hand_ids)==2 for x in out if x.gesture)


@pytest.mark.parametrize('pose,opposite',[('V',True),('L',False)])
def test_two_v_or_parallel_l_do_not_capture(pose,opposite):
    r=GestureRecognizer()
    assert events([r.process(l_frame(1000+t,pose,opposite),True) for t in range(0,1001,50)])==[]


def test_stop_preempts_two_hand_candidate():
    r=GestureRecognizer()
    for t in range(0,751,50):r.process(l_frame(1000+t),True)
    out=[r.process(frame(1800+t,sample_hand('THREE','left'),sample_hand('L','right')),True) for t in range(0,401,50)]
    assert events(out)==[Gesture.STOP]


@pytest.mark.parametrize('phase',[0,45,90,135,180,225,270,315])
def test_wide_circle_initial_arc_never_emits_swipe(phase):
    r=GestureRecognizer()
    assert events([r.process(f,True) for f in circle_frames(radius=.18,phase=phase)])==[Gesture.CIRCLE]


def test_three_interrupts_waiting_v_hold():
    r=GestureRecognizer()
    for t in range(0,551,50):r.process(sample_frame(1000+t,'V'),False)
    r.process(sample_frame(1575,'THREE'),False)
    assert r.process(sample_frame(1600,'V'),False).gesture is None


def test_short_fists_cannot_accumulate_across_open_pose():
    r=GestureRecognizer();out=[]
    for start in (1000,1300):
        for t in range(0,201,50):out.append(r.process(sample_frame(start+t,'FIST'),True))
        out.append(r.process(sample_frame(start+250,'OPEN'),True))
    for t in range(1600,1801,50):out.append(r.process(sample_frame(t,'OPEN'),True))
    assert events(out)==[]
