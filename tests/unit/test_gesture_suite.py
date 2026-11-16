from dataclasses import replace
import json
from pathlib import Path

import pytest

from hand_v2.domain.models import TrackingFrame,Hand,Landmark,Result,Status,Action
from hand_v2.domain.recognition import GestureRecognizer
from tests.unit.test_vision_control import rig,feed


SUITE=json.loads((Path(__file__).parents[1]/'fixtures/gesture_suite.json').read_text(encoding='utf-8'))

def deserialize(value):
    return TrackingFrame(**{**value,'hands':tuple(Hand(**{**h,'landmarks':tuple(Landmark(**p) for p in h['landmarks'])}) for h in value['hands'])})


def test_all_gesture_fixtures_repeat_ten_times_without_os_adapter(monkeypatch):
    from hand_v2.adapters.windows.native import Win32
    def forbidden(*a,**kw):raise AssertionError('OS adapter must not be constructed')
    monkeypatch.setattr(Win32,'__init__',forbidden)
    assert {g for c in SUITE['cases'] for g in c['expected']}=={f'G{i:02d}' for i in range(1,15)}
    for _ in range(10):
        for case in SUITE['cases']:
            recognizer=GestureRecognizer();events=[]
            for value in case['frames']:
                result=recognizer.process(deserialize(value),case['active'])
                if result.gesture:events.append(result.gesture.value)
            assert events==case['expected'],case['name']


@pytest.mark.parametrize('gesture,chord',[
    ('G03',('ALT','LEFT')),('G04',('ALT','RIGHT')),('G05',('CTRL','SHIFT','TAB')),
    ('G06',('CTRL','TAB')),('G07',('PAGEUP',)),('G08',('PAGEDOWN',)),
    ('G09',('CTRL','ADD')),('G10',('CTRL','SUBTRACT')),('G11',('CTRL','R')),
    ('G12',('CTRL','D')),('G13',('CTRL','SHIFT','T')),('G14',None)])
def test_recognized_frames_reach_shortcut_or_fake_capture(gesture,chord):
    runtime,vision=rig();captured=[]
    class FakeCapture:
        def execute(self,command):
            captured.append(command.action)
            return Result(command.command_id,command.context_version,runtime.clock.now_ms(),Status.APPLIED,'FAKE_CAPTURE')
    runtime.controller.app_actions=FakeCapture()
    feed(runtime,vision,'V',1000,1600);feed(runtime,vision,'OPEN',1650,1850)
    case=next(c for c in SUITE['cases'] if c['expected']==[gesture])
    for value in case['frames']:
        original=deserialize(value);at=original.captured_at_ms+900
        frame=replace(original,frame_id=at,captured_at_ms=at)
        runtime.scheduler.advance_to(at);vision.accept(frame);runtime.controller.flush_executor()
    assert runtime.keyboard.sent_chords==([chord] if chord else [])
    assert captured==([Action.CAPTURE] if gesture=='G14' else [])
    if gesture=='G12':assert runtime.controller.state.confirmation_pending
