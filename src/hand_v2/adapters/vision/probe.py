"""Explicit camera diagnostic, also runnable inside the frozen executable.

This path never constructs a KeyboardPort and stores no camera images.
"""
from dataclasses import asdict
import time

from hand_v2.adapters.timing import MonotonicClock
from .supervisor import CameraSupervisor


def probe_camera(index=0,seconds=15):
    supervisor=CameraSupervisor(MonotonicClock());supervisor.start(index,preview=False)
    begin=time.monotonic();frames=[];errors=[];first=None
    try:
        while time.monotonic()-begin<seconds:
            for kind,value in supervisor.poll():
                if kind=='frame':
                    frame=value.frame
                    if first is None:first=time.monotonic()
                    frames.append({'frame_id':frame.frame_id,'age_ms':supervisor.clock.now_ms()-frame.captured_at_ms,
                                   'inference_ms':round(value.inference_ms,2),'hands':len(frame.hands),
                                   'preview_bytes':len(value.preview_rgb or b''),'size':[frame.image_width,frame.image_height]})
                elif kind=='error':errors.append(value)
            if errors:break
            time.sleep(.01)
    finally:
        stop_begin=time.monotonic();supervisor.stop()
        while supervisor.session and time.monotonic()-stop_begin<4.5:
            supervisor.poll();time.sleep(.01)
    success=bool(frames and not errors and supervisor.last_stop and supervisor.last_stop.success)
    return {'source':'REAL_CAMERA_MEDIAPIPE_VIDEO_NO_OS_INPUT','success':success,'index':index,'frames':len(frames),
            'startup_seconds':None if first is None else round(first-begin,3),
            'fps_after_start':0 if first is None else round(len(frames)/max(.01,stop_begin-first),2),
            'errors':errors,'stop':asdict(supervisor.last_stop) if supervisor.last_stop else None,
            'samples':frames,'raw_images_saved':False,'human_gesture_accuracy_evaluated':False}
