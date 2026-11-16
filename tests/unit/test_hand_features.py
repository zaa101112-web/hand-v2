from dataclasses import replace
import pytest

from tests.hand_samples import sample_hand
from hand_v2.domain.features import describe_hand,angle,FingerState,TimeEMA
from hand_v2.domain.tracking import HandIdentityTracker


@pytest.mark.parametrize('pose',['V','THREE','INDEX','OPEN','FIST','THUMB','L'])
def test_hand_authored_geometry_matches_pose(pose):
    features=describe_hand(sample_hand(pose),640,480)
    assert features.pose==pose
    assert features.palm_size>=20


def test_degenerate_and_too_small_hand_is_unknown():
    assert describe_hand(sample_hand(scale=.01),640,480).pose=='UNKNOWN'
    assert angle((0,0,0),(0,0,0),(1,0,0)) is None


def test_direction_is_mirrored_once_and_geometry_uses_pixels():
    hand=sample_hand('INDEX',offset=.1)
    features=describe_hand(hand,1280,720)
    assert features.pointer[0]==pytest.approx(1-hand.landmarks[8].x)
    assert features.pointer[1]==pytest.approx(hand.landmarks[8].y)
    assert features.palm_size>describe_hand(hand,640,480).palm_size


def test_time_ema_matches_elapsed_time_not_frame_count():
    a=TimeEMA(60);b=TimeEMA(60)
    a.update((0,0),0);b.update((0,0),0)
    end_a=a.update((1,0),60)
    for t in (20,40,60):end_b=b.update((1,0),t)
    assert end_a==pytest.approx(end_b)
    a.reset();assert a.update((3,4),100)==(3,4)


def test_hand_ids_survive_array_order_but_not_loss_or_ambiguous_crossing():
    tracker=HandIdentityTracker('test')
    left=sample_hand(offset=-.22);right=sample_hand(offset=.22)
    first=tracker.update((left,right),640,480)
    second=tracker.update((right,left),640,480)
    assert second[0].hand_id==first[1].hand_id and second[1].hand_id==first[0].hand_id
    tracker.update((),640,480)
    third=tracker.update((left,),640,480)
    assert third[0].hand_id not in {h.hand_id for h in first}
    ambiguous=tracker.update((sample_hand(offset=-.01),sample_hand(offset=.01)),640,480)
    assert len({h.hand_id for h in ambiguous})==2
    assert all(h.hand_id!=third[0].hand_id for h in ambiguous)


def test_handedness_label_is_not_hand_identity():
    tracker=HandIdentityTracker('test')
    hand=sample_hand();first=tracker.update((hand,),640,480)
    changed=tracker.update((replace(hand,handedness='LEFT'),),640,480)
    assert first[0].hand_id==changed[0].hand_id
