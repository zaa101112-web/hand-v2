"""Preparation motion must not poison a later, distinct swipe.

Authored paths reproduce the move/pause/swipe phases seen in diagnostic scalar
traces. These are not recorded coordinates or measured human accuracy.
"""
from dataclasses import replace

import pytest

from hand_v2.domain.models import Gesture
from hand_v2.domain.recognition import GestureRecognizer
from tests.hand_samples import sample_frame
from tests.unit.test_extended_recognition import circle_frames


def moved_frame(at,pose,dx=0,dy=0):
    frame=sample_frame(at,pose,dx)
    hand=frame.hands[0]
    return replace(frame,hands=(replace(hand,landmarks=tuple(replace(p,y=p.y+dy) for p in hand.landmarks)),))


@pytest.mark.parametrize('pose,direction,expected',[
    ('INDEX',1,Gesture.LEFT),('INDEX',-1,Gesture.RIGHT),
    ('V',1,Gesture.TAB_LEFT),('V',-1,Gesture.TAB_RIGHT),
])
@pytest.mark.parametrize('pause_ms',[400,1000,3000])
def test_move_to_pointing_pose_then_pause_then_swipe(pose,direction,expected,pause_ms):
    recognizer=GestureRecognizer();events=[]
    # Extending the finger moves its tip 8% vertically, then it settles.
    frames=[moved_frame(1000+t,pose,dy=-.08*t/150) for t in range(0,151,50)]
    frames += [moved_frame(1150+t,pose,dy=-.08+(1/480 if t%100 else 0)) for t in range(50,pause_ms+1,50)]
    frames += [moved_frame(1150+pause_ms+t,pose,direction*.24*t/500,-.08) for t in range(50,551,50)]
    for frame in frames:
        result=recognizer.process(frame,True)
        if result.gesture:events.append(result.gesture)
    assert events==[expected]


def test_small_preparation_reversal_then_pause_does_not_lock_circle_candidate():
    recognizer=GestureRecognizer();events=[]
    offsets=[0,.02,.04,.06,.04,.03]
    frames=[moved_frame(1000+i*50,'INDEX',dx) for i,dx in enumerate(offsets)]
    frames += [moved_frame(t,'INDEX',.03) for t in range(1300,2101,50)]
    frames += [moved_frame(2100+t,'INDEX',.03+.24*t/500) for t in range(50,551,50)]
    for frame in frames:
        result=recognizer.process(frame,True)
        if result.gesture:events.append(result.gesture)
    assert events==[Gesture.LEFT]


def test_pause_after_success_never_rearms_a_second_command():
    recognizer=GestureRecognizer();events=[]
    frames=[moved_frame(1000+t,'INDEX',.24*t/500) for t in range(0,501,50)]
    frames += [moved_frame(t,'INDEX',.24) for t in range(1550,3001,50)]
    frames += [moved_frame(3000+t,'INDEX',.24-.24*t/500) for t in range(50,551,50)]
    for frame in frames:
        result=recognizer.process(frame,True)
        if result.gesture:events.append(result.gesture)
    assert events==[Gesture.LEFT]


@pytest.mark.parametrize('phase',[0,45,90,135,180,225,270,315])
@pytest.mark.parametrize('radius',[.04,.10,.18])
def test_continuous_circle_is_not_reset_as_a_preparation_pause(phase,radius):
    recognizer=GestureRecognizer()
    out=[recognizer.process(frame,True) for frame in circle_frames(radius=radius,phase=phase,duration=2000)]
    # The minimum radius can be reduced by EMA and rejected; it must not swipe.
    expected=[] if radius==.04 else [Gesture.CIRCLE]
    assert [r.gesture for r in out if r.gesture]==expected
