"""Authored geometry reproducing joint angles observed in the user's diagnostic.

These are not recorded landmark trajectories or a measured accuracy result.
"""
from dataclasses import replace
import math

import pytest

from hand_v2.domain.features import describe_hand,FingerState
from hand_v2.domain.models import Gesture,Landmark,TrackingFrame
from hand_v2.domain.recognition import GestureRecognizer
from tests.hand_samples import sample_hand,sample_frame
from tests.unit.test_index_swipe_regression import bent_thumb_hand


def with_bent_finger(hand,pip,dip,base=17):
    points=list(hand.landmarks)
    origin=points[base]
    x,y=origin.x*640,origin.y*480
    direction=-math.pi/2
    for index,length,turn in ((base+1,44,0),(base+2,34,180-pip),(base+3,28,180-dip)):
        direction+=math.radians(turn)
        x+=length*math.cos(direction);y+=length*math.sin(direction)
        points[index]=Landmark(x/640,y/480)
    return replace(hand,landmarks=tuple(points))


@pytest.mark.parametrize('pip,dip',[(123.5228094,118.4008724),(123.0783434,136.1655656),(123.9776854,103.9733278),(134.6,109.9),(145,140)])
def test_both_bent_pinky_joints_support_index_even_when_pip_exceeds_120(pip,dip):
    feature=describe_hand(with_bent_finger(sample_hand('INDEX'),pip,dip),640,480)
    assert feature.fingers[4]==FingerState.UNKNOWN  # Preserve the strict raw classification.
    assert feature.pose=='INDEX'


@pytest.mark.parametrize('base',[9,13])
def test_same_two_joint_evidence_applies_to_other_tucked_fingers(base):
    assert describe_hand(with_bent_finger(sample_hand('INDEX'),130,130,base),640,480).pose=='INDEX'


@pytest.mark.parametrize('pip,dip',[(145.01,140),(145,140.01),(150,130),(130,150),(170,170)])
def test_unproven_or_extended_pinky_is_not_silently_ignored(pip,dip):
    assert describe_hand(with_bent_finger(sample_hand('INDEX'),pip,dip),640,480).pose!='INDEX'


@pytest.mark.parametrize('direction,expected',[(1,Gesture.LEFT),(-1,Gesture.RIGHT)])
def test_pinky_crossing_old_fold_boundary_does_not_cancel_swipe(direction,expected):
    recognizer=GestureRecognizer();events=[]
    for elapsed in range(0,501,50):
        hand=sample_hand('INDEX',offset=direction*.24*elapsed/500)
        hand=with_bent_finger(hand,110 if elapsed%100==0 else 128,120)
        result=recognizer.process(TrackingFrame(1000+elapsed,1000+elapsed,1,640,480,(hand,)),True)
        if result.gesture:events.append(result.gesture)
    assert events==[expected]


def test_supported_thumb_and_tucked_pinky_work_together():
    hand=with_bent_finger(bent_thumb_hand(140,155),130,130)
    assert describe_hand(hand,640,480).pose=='INDEX'


@pytest.mark.parametrize('pose',['V','THREE','L','OPEN','FIST'])
def test_index_exception_does_not_reclassify_other_poses(pose):
    hand=with_bent_finger(sample_hand(pose),130,130)
    assert describe_hand(hand,640,480).pose!='INDEX'


def test_no_start_or_stop_from_index_specific_fold_evidence():
    hand=with_bent_finger(sample_hand('V'),130,130)
    for active in (False,True):
        recognizer=GestureRecognizer()
        assert not any(recognizer.process(TrackingFrame(t,t,1,640,480,(hand,)),active).gesture for t in range(1000,2001,50))


def test_truly_ambiguous_frame_still_cancels_path():
    recognizer=GestureRecognizer();events=[]
    for elapsed in range(0,501,50):
        hand=sample_hand('INDEX',offset=.24*elapsed/500)
        hand=with_bent_finger(hand,150 if elapsed==250 else 130,130)
        result=recognizer.process(TrackingFrame(1000+elapsed,1000+elapsed,1,640,480,(hand,)),True)
        if result.gesture:events.append(result.gesture)
    assert events==[]


def test_tucked_finger_rule_does_not_bypass_small_hand_gate():
    hand=with_bent_finger(sample_hand('INDEX'),130,130)
    hand=replace(hand,landmarks=tuple(replace(p,x=.5+(p.x-.5)*.05,y=.5+(p.y-.5)*.05) for p in hand.landmarks))
    assert describe_hand(hand,640,480).pose=='UNKNOWN'


def test_remaining_pinky_ambiguity_names_the_finger_to_adjust():
    hand=with_bent_finger(sample_hand('INDEX'),150,150)
    result=GestureRecognizer().process(TrackingFrame(1000,1000,1,640,480,(hand,)),True)
    assert result.gesture is None
    assert '새끼손가락' in result.candidate
