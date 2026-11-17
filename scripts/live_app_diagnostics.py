"""Actual Qt app and actual camera; diagnostic state only, no image recording or fake gestures."""
import argparse,json,multiprocessing,sys
from collections import Counter,deque
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--camera',type=int,default=1);p.add_argument('--seconds',type=int,default=0,help='0 keeps the diagnostic app open until the user closes it')
    p.add_argument('--label',default='m04-live-app')
    p.add_argument('--output',type=Path,help='Explicit local diagnostic output path')
    args=p.parse_args()
    if not args.label.replace('-','').isalnum():p.error('invalid label')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from hand_v2.bootstrap import build_runtime
    from hand_v2.adapters.qt.window import MainWindow
    app=QApplication([]);runtime=build_runtime('WINDOWS_REAL');window=MainWindow(runtime)
    window.camera_combo.setCurrentIndex(args.camera);window.show()
    output=args.output or ROOT/f'docs/validation/{args.label}.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    from hand_v2.domain.features import describe_hand,angle,distance
    samples=deque(maxlen=900);counts=Counter();last_frame_at=None;last_had_hands=False
    original_accept=runtime.vision.accept
    def observe_frame(frame):
        nonlocal last_frame_at,last_had_hands
        accepted=original_accept(frame)
        gap=None if last_frame_at is None else frame.captured_at_ms-last_frame_at
        last_frame_at=frame.captured_at_ms
        features=[describe_hand(h,frame.image_width,frame.image_height) for h in frame.hands]
        counts['frames']+=1;counts['with_hands']+=bool(features)
        counts['gap_over_100ms']+=gap is not None and gap>100
        result=runtime.vision.last_recognition if accepted else None
        counts['rejected_frames']+=not accepted
        if result:counts['reason_'+(result.reason or 'NONE')]+=1
        for f in features:
            counts['pose_'+f.pose]+=1
            if f.pose=='UNKNOWN':counts['unknown_fingers_'+'_'.join(f.fingers)]+=1
        # Keep every hand-present frame: a single bad frame cancels a path and
        # was invisible in the old 100ms diagnostic sampling interval.
        # One no-hand transition cancels a path. Repeated empty frames should
        # not erase the useful hand samples while the user types their reply.
        if features or last_had_hands:
            details=[]
            for hand,f in zip(frame.hands,features):
                points=[(lm.x*frame.image_width,lm.y*frame.image_height,lm.z*frame.image_width) for lm in hand.landmarks]
                details.append({'id':hand.hand_id,'pose':f.pose,'fingers':f.fingers,'palm_px':round(f.palm_size,1),
                                'thumb_angles':[angle(*points[1:4]),angle(*points[2:5])],
                                'thumb_gap_ratio':distance(points[4],points[5])/max(f.palm_size,1e-9),
                                'finger_pip_dip':[[angle(*points[b:b+3]),angle(*points[b+1:b+4])] for b in (5,9,13,17)]})
            motion=runtime.vision.recognizer.motion
            motion_summary=None
            if motion.path:
                length=sum(distance(a[1],b[1]) for a,b in zip(motion.path,motion.path[1:]))
                displacement=distance(motion.path[0][1],motion.path[-1][1])
                motion_summary={'elapsed_ms':None if motion.since is None else frame.captured_at_ms-motion.since,
                                'curved':motion.curved,'curve_reason':motion.curve_reason,
                                'straightness':round(displacement/length,4) if length else None,
                                'travel':round(length,4)}
            samples.append({'at_ms':frame.captured_at_ms,'gap_ms':gap,'accepted':accepted,'hands':details,
                            'candidate':result.candidate if result else None,'progress':result.progress if result else 0,
                            'reason':result.reason if result else None,'gesture':result.gesture if result else None,
                            'motion':motion_summary})
        last_had_hands=bool(features)
        return accepted
    runtime.vision.accept=observe_frame
    observations=[]
    last=None
    def snapshot():
        nonlocal last
        state=asdict(runtime.controller.state)
        observation={k:state[k] for k in ('activation','ready','last_candidate','last_execution','last_stop_reason')}
        if observation!=last:
            last=observation;observations.append({'at_ms':runtime.clock.now_ms(),**observation})
            del observations[:-500]
        data={'at_utc':datetime.now(timezone.utc).isoformat(),'monotonic_at_ms':runtime.clock.now_ms(),
              'state':state,'fps':runtime.camera_fps,'recognized_events':[asdict(e) for e in runtime.vision.recognized_events],
              'observations':observations,
              'tracking_counts':dict(counts),'recent_pose_samples':list(samples),
              'camera_stop':asdict(runtime.camera.last_stop) if runtime.camera.last_stop else None,
              'hotkey_registered':bool(window.hotkey and window.hotkey.registered),'raw_images_saved':False}
        output.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),default=lambda o:sorted(o) if isinstance(o,frozenset) else str(o)),encoding='utf-8')
    timer=QTimer();timer.timeout.connect(snapshot);timer.start(500)
    QTimer.singleShot(500,lambda:runtime.start_camera(args.camera,True))
    if args.seconds>0:QTimer.singleShot(args.seconds*1000,window.close)
    result=app.exec();snapshot()
    return result if window.shutdown_ok else 2


if __name__=='__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
