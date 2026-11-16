"""Opt-in real camera/model probe; never saves camera images or sends keyboard input."""
import argparse,json,multiprocessing,time,sys
from dataclasses import asdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=12);parser.add_argument('--index',type=int,default=0);parser.add_argument('--label',default='m03-camera-hardware')
    args=parser.parse_args()
    from hand_v2.adapters.vision.supervisor import CameraSupervisor
    from hand_v2.adapters.timing import MonotonicClock
    supervisor=CameraSupervisor(MonotonicClock());supervisor.start(args.index,preview=False)
    begin=time.monotonic();frames=[];errors=[];first=None
    while time.monotonic()-begin<args.seconds:
        for kind,value in supervisor.poll():
            if kind=='frame':
                f=value.frame
                if first is None:first=time.monotonic()
                frames.append({'frame_id':f.frame_id,'captured_at_ms':f.captured_at_ms,'age_ms':supervisor.clock.now_ms()-f.captured_at_ms,
                               'inference_ms':round(value.inference_ms,2),'hands':len(f.hands),'preview_bytes':len(value.preview_rgb or b''),'size':[f.image_width,f.image_height]})
            elif kind=='error':errors.append(value)
        if errors:break
        time.sleep(.01)
    stop_begin=time.monotonic();supervisor.stop()
    while supervisor.session and time.monotonic()-stop_begin<4.5:
        supervisor.poll();time.sleep(.01)
    report={'source':'REAL_CAMERA_MEDIAPIPE_VIDEO_NO_OS_INPUT','index':args.index,'frames':len(frames),
            'startup_seconds':None if first is None else round(first-begin,3),
            'fps_after_start':0 if first is None else round(len(frames)/max(.01,stop_begin-first),2),
            'errors':errors,'stop':asdict(supervisor.last_stop) if supervisor.last_stop else None,
            'samples':frames,'raw_images_saved':False,'human_gesture_accuracy_evaluated':False}
    (ROOT/'docs/validation'/f'{args.label}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
    return 0 if frames and not errors and supervisor.last_stop and supervisor.last_stop.success else 1


if __name__=='__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
