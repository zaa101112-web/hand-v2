"""Regression geometry for thumb ambiguity and waiting before a swipe.

Angles are inspired by observed diagnostic ranges; these are authored landmarks,
not recorded user images or a claim of human recognition accuracy.
"""
from dataclasses import replace
import math

import pytest

from hand_v2.domain.features import describe_hand
from hand_v2.domain.models import Gesture,Landmark,TrackingFrame
from hand_v2.domain.recognition import GestureRecognizer
from tests.hand_samples import sample_hand,sample_frame


def bent_thumb_hand(mcp=140,ip=155,pose='INDEX',offset=0):
    hand=sample_hand(pose,offset=offset)
    points=list(hand.landmarks)
    theta=math.radians(180-mcp);after=theta+math.radians(180-ip)
    joint=(200+40*math.cos(theta),320+40*math.sin(theta))
    tip=(joint[0]+35*math.cos(after),joint[1]+35*math.sin(after))
    for i,(x,y) in enumerate(((160,320),(200,320),joint,tip),1):
        points[i]=Landmark(x/640+offset,y/480)
    return replace(hand,landmarks=tuple(points))


@pytest.mark.parametrize('mcp,ip',[(133.8,147.2),(140,155),(155,140),(145,155)])
def test_index_with_bent_thumb_does_not_require_tightly_closed_thumb(mcp,ip):
    assert describe_hand(bent_thumb_hand(mcp,ip),640,480).pose=='INDEX'


@pytest.mark.parametrize('mcp,ip',[(145.01,155),(155,145.01),(150,150)])
def test_nearly_extended_thumb_stays_ambiguous(mcp,ip):
    assert describe_hand(bent_thumb_hand(mcp,ip),640,480).pose!='INDEX'


def test_thumb_exception_never_turns_ambiguous_v_into_start_or_stop():
    hand=bent_thumb_hand(pose='V')
    assert describe_hand(hand,640,480).pose=='UNKNOWN'
    for active in (False,True):
        r=GestureRecognizer()
        assert not any(r.process(TrackingFrame(t,t,1,640,480,(hand,)),active).gesture for t in range(1000,2001,50))


@pytest.mark.parametrize('pose,expected',[('INDEX',Gesture.LEFT),('V',Gesture.TAB_LEFT)])
@pytest.mark.parametrize('hold_ms',[1000,4000])
def test_pose_can_be_held_before_swipe_without_expiring_motion(pose,expected,hold_ms):
    r=GestureRecognizer();events=[]
    for t in range(0,hold_ms+1,50):
        assert r.process(sample_frame(1000+t,pose),True).gesture is None
    for t in range(50,551,50):
        result=r.process(sample_frame(1000+hold_ms+t,pose,.24*t/500),True)
        if result.gesture:events.append(result.gesture)
    assert events==[expected]


@pytest.mark.parametrize('direction,expected',[(1,Gesture.LEFT),(-1,Gesture.RIGHT)])
def test_thumb_angle_changes_during_swipe_do_not_discard_index_path(direction,expected):
    r=GestureRecognizer();events=[]
    for t in range(0,501,50):
        hand=bent_thumb_hand(125 if t%100==0 else 140,155,offset=direction*.24*t/500)
        result=r.process(TrackingFrame(1000+t,1000+t,1,640,480,(hand,)),True)
        if result.gesture:events.append(result.gesture)
    assert events==[expected]


def test_held_l_and_fist_are_not_index_swipes():
    for pose in ('L','FIST'):
        r=GestureRecognizer()
        assert not any(r.process(sample_frame(1000+t,pose,.24*t/500),True).gesture for t in range(0,501,50))


def test_small_hand_does_not_use_thumb_exception():
    hand=bent_thumb_hand()
    hand=replace(hand,landmarks=tuple(replace(p,x=.5+(p.x-.5)*.05,y=.5+(p.y-.5)*.05) for p in hand.landmarks))
    assert describe_hand(hand,640,480).pose=='UNKNOWN'


def test_relaxed_index_still_requires_active_control():
    r=GestureRecognizer()
    for t in range(0,501,50):
        hand=bent_thumb_hand(offset=.24*t/500)
        assert r.process(TrackingFrame(1000+t,1000+t,1,640,480,(hand,)),False).gesture is None


def test_ambiguous_thumb_above_bound_cancels_old_motion():
    r=GestureRecognizer();events=[]
    for t in range(0,501,50):
        hand=bent_thumb_hand(mcp=148 if t==250 else 140,offset=.24*t/500)
        result=r.process(TrackingFrame(1000+t,1000+t,1,640,480,(hand,)),True)
        if result.gesture:events.append(result.gesture)
    assert events==[]


def test_circle_after_stationary_pointing_still_excludes_swipe():
    from tests.unit.test_extended_recognition import circle_frames
    r=GestureRecognizer();frames=list(circle_frames());first=frames[0]
    for at in range(1000,3000,50):
        assert r.process(replace(first,frame_id=at,captured_at_ms=at),True).gesture is None
    events=[]
    for frame in frames:
        result=r.process(replace(frame,frame_id=frame.frame_id+2000,captured_at_ms=frame.captured_at_ms+2000),True)
        if result.gesture:events.append(result.gesture)
    assert events==[Gesture.CIRCLE]
