"""A slow patch and a few pixels of lateral jitter must not turn a swipe into a circle.

Paths are authored failure cases, not recorded camera coordinates.
"""
from dataclasses import replace
import pytest

from hand_v2.domain.recognition import GestureRecognizer
from hand_v2.domain.models import Gesture
from tests.hand_samples import sample_frame


@pytest.mark.parametrize('pose,direction,expected',[
    ('INDEX',1,Gesture.LEFT),('INDEX',-1,Gesture.RIGHT),
    ('V',1,Gesture.TAB_LEFT),('V',-1,Gesture.TAB_RIGHT),
])
@pytest.mark.parametrize('size',[(640,480),(1280,960),(1280,720)])
def test_nearly_straight_swipe_with_brief_slowdown_and_small_vertical_jitter(pose,direction,expected,size):
    recognizer=GestureRecognizer();events=[]
    offsets=[0,.03,.06,.09,.12,.14,.14,.14,.17,.20,.23,.26,.30]
    for index,offset in enumerate(offsets):
        frame=sample_frame(1000+50*index,pose,direction*offset)
        jitter=4/480 if index==7 else 0
        hand=frame.hands[0]
        hand=replace(hand,landmarks=tuple(replace(p,y=p.y+jitter) for p in hand.landmarks))
        result=recognizer.process(replace(frame,hands=(hand,),image_width=size[0],image_height=size[1]),True)
        if result.gesture:events.append(result.gesture)
    assert events==[expected]


@pytest.mark.parametrize('direction,expected',[(-1,Gesture.PAGE_UP),(1,Gesture.PAGE_DOWN)])
def test_vertical_v_swipe_ignores_small_horizontal_jitter(direction,expected):
    recognizer=GestureRecognizer();events=[]
    offsets=[0,.03,.06,.09,.12,.14,.14,.14,.17,.20,.23,.26,.30]
    for index,offset in enumerate(offsets):
        frame=sample_frame(1000+50*index,'V')
        jitter=4/640 if index==7 else 0
        hand=frame.hands[0]
        hand=replace(hand,landmarks=tuple(replace(p,x=p.x+jitter,y=p.y+direction*offset) for p in hand.landmarks))
        result=recognizer.process(replace(frame,hands=(hand,)),True)
        if result.gesture:events.append(result.gesture)
    assert events==[expected]


@pytest.mark.parametrize('phase',[45,225])
@pytest.mark.parametrize('direction',[-1,1])
@pytest.mark.parametrize('duration',[600,2000])
def test_resampled_direction_preserves_circle_protection_at_time_bounds(phase,direction,duration):
    from tests.unit.test_extended_recognition import circle_frames
    recognizer=GestureRecognizer()
    results=[recognizer.process(f,True) for f in circle_frames(radius=.18,phase=phase,direction=direction,duration=duration)]
    assert [r.gesture for r in results if r.gesture]==[Gesture.CIRCLE]
