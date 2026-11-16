from dataclasses import replace
import pytest
from tests.hand_samples import sample_frame,sample_hand
from hand_v2.domain.recognition import GestureRecognizer
from hand_v2.domain.models import Gesture,TrackingFrame


def feed_hold(recognizer,pose,duration,active=False,hand_id='h1',start=1000):
    results=[]
    for elapsed in list(range(0,duration,50))+[duration]:
        results.append(recognizer.process(sample_frame(start+elapsed,pose,hand_id=hand_id),active))
    return results


@pytest.mark.parametrize('duration,expected',[(599,False),(600,True),(601,True)])
def test_v_start_continuous_hold_boundary(duration,expected):
    results=feed_hold(GestureRecognizer(),'V',duration)
    assert any(r.gesture==Gesture.START for r in results)==expected


@pytest.mark.parametrize('duration,expected',[(349,False),(350,True),(351,True)])
def test_three_stop_continuous_hold_boundary(duration,expected):
    results=feed_hold(GestureRecognizer(),'THREE',duration,True)
    assert any(r.gesture==Gesture.STOP for r in results)==expected


def test_same_pose_held_does_not_repeat_and_open_palm_is_not_stop():
    r=GestureRecognizer()
    output=feed_hold(r,'V',1200)
    assert [x.gesture for x in output if x.gesture]==[Gesture.START]
    output=feed_hold(r,'OPEN',700,True,start=2250)
    assert not any(x.gesture for x in output)
    assert all(x.neutral for x in output)


def test_gap_loss_id_epoch_reset_do_not_inherit_hold():
    for kind in ('gap','loss','id','epoch'):
        r=GestureRecognizer();feed_hold(r,'V',550)
        if kind=='loss':r.process(TrackingFrame(1575,1575,1,640,480,()),False)
        f=sample_frame(1700 if kind=='gap' else 1600,'V',hand_id='h2' if kind=='id' else 'h1',epoch=2 if kind=='epoch' else 1)
        assert r.process(f,False).gesture is None


def test_same_or_reverse_frame_timestamp_cannot_complete_gesture():
    r=GestureRecognizer();feed_hold(r,'V',550)
    assert r.process(sample_frame(1550,'V'),False).reason=='STALE_FRAME'
    assert r.process(sample_frame(1549,'V'),False).reason=='STALE_FRAME'


def test_stop_is_detected_even_when_general_gestures_are_not_ready():
    r=GestureRecognizer()
    out=feed_hold(r,'THREE',400,True)
    assert [x.gesture for x in out if x.gesture]==[Gesture.STOP]


@pytest.mark.parametrize('direction,gesture',[(1,Gesture.LEFT),(-1,Gesture.RIGHT)])
def test_index_swipe_mirrors_once_and_emits_once(direction,gesture):
    r=GestureRecognizer();out=[]
    for t in range(0,501,50):
        out.append(r.process(sample_frame(1000+t,'INDEX',direction*.24*t/500),True))
    assert [x.gesture for x in out if x.gesture]==[gesture]
    for t in (1550,1600,1650):assert r.process(sample_frame(t,'INDEX',direction*.3),True).gesture is None


def test_short_slow_and_diagonal_swipes_do_not_execute():
    for kind in ('short','slow','diagonal'):
        r=GestureRecognizer();out=[]
        for t in range(0,1001,50):
            dx=(.08 if kind=='short' else .16)*t/1000
            f=sample_frame(1000+t,'INDEX',dx)
            if kind=='diagonal':
                hand=f.hands[0]
                points=tuple(replace(p,y=p.y+dx) for p in hand.landmarks)
                f=replace(f,hands=(replace(hand,landmarks=points),))
            out.append(r.process(f,True))
        assert not any(x.gesture for x in out)
