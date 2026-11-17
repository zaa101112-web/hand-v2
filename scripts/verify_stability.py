"""20-minute actual camera/model/Qt run with exclusively fake action outputs."""
from pathlib import Path
import argparse,json,sys,time,multiprocessing,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--camera',type=int,default=1)
    parser.add_argument('--seconds',type=int,default=1200);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from hand_v2.bootstrap import build_runtime
    from hand_v2.adapters.qt.window import MainWindow
    from hand_v2.adapters.vision.supervisor import CameraSupervisor
    app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    r=build_runtime();camera=CameraSupervisor(r.clock)
    samples=[];errors=[];first=None;start=time.monotonic();last_report=start
    class ObservedCamera:
        def __getattr__(self,name):return getattr(camera,name)
        def poll(self):
            nonlocal first
            events=camera.poll()
            for kind,value in events:
                if kind=='frame':
                    if first is None:first=time.monotonic()
                    samples.append((r.clock.now_ms()-value.frame.captured_at_ms,value.inference_ms,len(value.frame.hands)))
                elif kind=='error':errors.append(value)
            return events
    r.camera=ObservedCamera()
    window=MainWindow(r);window.setWindowTitle('HAND — 20분 자동 안정성 검사 (실제 카메라 / 가상 출력)')
    window.banner.setText('자동 안정성 검사 중 · 카메라/모델/화면 갱신 · 실제 키 입력과 화면 저장 없음')
    window.show();window.select_page('practice');r.start_camera(args.camera,True)
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*.py'))}
    finished=False
    def finish():
        nonlocal finished
        if finished:return
        finished=True;timer.stop();elapsed=time.monotonic()-(first or start)
        def p95(values):return sorted(values)[min(len(values)-1,int(len(values)*.95))] if values else None
        data={'source':'actual camera + MediaPipe + Qt event loop; fake actions, not human recognition accuracy',
              'seconds_after_first_frame':round(elapsed,3),'required_seconds':args.seconds,'frames':len(samples),
              'fps':round(len(samples)/max(.001,elapsed),2),'frame_arrival_p95_ms':p95([v[0] for v in samples]),
              'inference_p95_ms':p95([v[1] for v in samples]),'errors':errors,'actual_keys_sent':0,
              'raw_images_saved':False,'source_hashes':source_hashes,'camera_index':args.camera,
              'status':'PASS' if first and elapsed>=args.seconds and len(samples)/elapsed>=20 and not errors else 'FAIL'}
        window.close()
        def complete():
            data['shutdown_ok']=window.shutdown_ok and camera.session is None
            if not data['shutdown_ok']:data['status']='FAIL'
            output=ROOT/args.output;output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(data,indent=2),encoding='utf-8');app.exit(0 if data['status']=='PASS' else 1)
        QTimer.singleShot(4600,complete)
    def tick():
        nonlocal last_report
        now=time.monotonic()
        if errors or (first is None and now-start>15) or (first is not None and now-first>=args.seconds):finish();return
        if now-last_report>=60:
            last_report=now;print(json.dumps({'elapsed':round(now-(first or start)),'frames':len(samples),'errors':errors}),flush=True)
    timer=QTimer();timer.timeout.connect(tick);timer.start(50)
    return app.exec()


if __name__=='__main__':
    multiprocessing.freeze_support();raise SystemExit(main())
