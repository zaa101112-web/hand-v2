"""Authored, repeatable landmarks. No recorded person and no camera model inference."""
from dataclasses import replace
import math
import random
from hand_v2.domain.models import Gesture
from tests.hand_samples import sample_frame
from tests.unit.test_extended_recognition import zoom_frame
from tests.unit.test_motion_preparation import moved_frame


def continuous_frames(interval=40,noise_px=0,seed=0):
    rng=random.Random(seed)
    for at in range(1000,44000,interval):
        if at<1900:f=sample_frame(at,'V')
        elif at<4000:f=sample_frame(at,'INDEX')
        else:
            index=(at-4000)//5000;t=(at-4000)%5000
            amount=min(1,max(0,(t-700)/500))*.24
            if index==0:f=moved_frame(at,'INDEX',amount)
            elif index==1:f=moved_frame(at,'INDEX',.24-amount)
            elif index==2:f=moved_frame(at,'V',amount)
            elif index==3:f=moved_frame(at,'V',.24-amount)
            elif index==4:f=moved_frame(at,'V',dy=amount)
            elif index==5:f=moved_frame(at,'V',dy=.24-amount)
            else:
                # Two gradual moves with a stable endpoint; never unpinch.
                a=min(1,max(0,(t-700)/600));b=min(1,max(0,(t-2600)/600))
                sep=.50+.15*a+.20*b if index==6 else .85-.20*a-.15*b
                f=zoom_frame(at,sep)
        if noise_px:
            # Rigid hand jitter retains hand shape; this is not joint/pose noise.
            dx=rng.uniform(-noise_px,noise_px)/640;dy=rng.uniform(-noise_px,noise_px)/480
            f=replace(f,hands=tuple(replace(h,landmarks=tuple(replace(p,x=p.x+dx,y=p.y+dy) for p in h.landmarks)) for h in f.hands))
        yield f


def run_continuous_case(interval=40,noise_px=0,seed=0):
    from hand_v2.bootstrap import build_runtime
    from hand_v2.adapters.timing import ManualClock
    from hand_v2.domain.assessment import ContinuousAssessment
    from hand_v2.domain.models import Status
    r=build_runtime(clock=ManualClock(1000))
    r.controller.begin_camera(1);r.controller.camera_connected(1)
    a=ContinuousAssessment('SYNTHETIC_LANDMARKS');a.start(1000)
    trace=[]
    for frame in continuous_frames(interval,noise_px,seed):
        at=frame.captured_at_ms;r.scheduler.advance_to(at)
        r.vision.accept(frame);r.controller.flush_executor()
        recognition=r.vision.last_recognition
        if recognition.gesture:
            command=r.vision.last_command;result=r.controller.state.last_execution
            ok=bool(command and result and command.command_id==result.command_id and result.status==Status.SENT)
            if recognition.gesture==Gesture.START:ok=True
            a.observe(at,recognition.gesture,ok)
            trace.append(dict(at_ms=at,gesture=recognition.gesture.value,executed=ok))
    a.tick(44000);report=a.report()
    report.update(interval_ms=interval,rigid_jitter_px=noise_px,seed=seed,trace=trace,
                  sent_chords=r.keyboard.sent_chords,owned_keys=list(r.controller.state.keyboard_state.owned_keys))
    r.close()
    return report
