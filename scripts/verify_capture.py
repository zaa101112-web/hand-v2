"""Opt-in live Windows QA of HAND's own capture UI against a controlled solid window.

No camera, synthetic gesture, external-app input or personal desktop image is used.
"""
from pathlib import Path
import argparse,json,sys,time,multiprocessing
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ack-screen-capture',action='store_true',required=True)
    parser.add_argument('--output',required=True);args=parser.parse_args()
    from PySide6.QtWidgets import QApplication,QWidget
    from PySide6.QtCore import QTimer,Qt
    from PIL import Image,ImageChops
    from hand_v2.bootstrap import build_runtime
    from hand_v2.domain.models import ExecutionMode
    from hand_v2.domain.capture import Rect
    from hand_v2.adapters.qt.window import MainWindow
    app=QApplication([])
    background=QWidget();background.setWindowTitle('HAND capture QA — controlled solid background')
    background.setStyleSheet('background:rgb(211,31,91);');background.showFullScreen()
    runtime=build_runtime(ExecutionMode.REAL)
    runtime.capture_folder=ROOT/'.build-staging'/'capture-qa'
    window=MainWindow(runtime)
    report={'kind':'actual Windows screen capture; controlled pixels; production hide/save path', 'status':'RUNNING','regions':[]}
    started=time.monotonic();phase=-1;case_index=0;baseline=None;baseline_at=0
    def finish(error=''):
        nonlocal phase
        if phase==99:return
        phase=99;timer.stop()
        if error:report.update(status='FAIL',error=error)
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        output=ROOT/args.output;output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        window.close();background.close();app.exit(0 if report['status']=='PASS' else 1)
    def tick():
        nonlocal phase,case_index,baseline,baseline_at
        if time.monotonic()-started>60:return finish('TIMEOUT')
        if phase==-1 and time.monotonic()-started>1:
            import mss,hashlib
            with mss.mss() as screen:
                shot=screen.grab(screen.monitors[1]);baseline=Image.frombytes('RGB',shot.size,shot.rgb)
            report['baseline_sha256']=hashlib.sha256(baseline.tobytes()).hexdigest()
            report['baseline_rgb_extrema']=baseline.getextrema()
            baseline_at=time.monotonic();window.show();window.raise_();phase=0
        elif phase==0 and time.monotonic()-baseline_at>.5 and not runtime.capture_worker.busy:
            runtime.workspace.request_capture();phase=1
        elif phase==1 and window.capture_ui.overlay:
            s=runtime.workspace.capture
            # Interior pixels are covered by the real HAND UI/overlay before hiding.
            w,h=s.display.width,s.display.height
            regions=[Rect(300,300,620,540),Rect(0,0,w,h),Rect(0,0,32,32),Rect(w-32,0,w,32),
                     Rect(0,h-32,32,h),Rect(w-32,h-32,w,h),Rect(1,1,101,101),Rect(15,15,255,255),
                     Rect(w//4,h//4,w*3//4,h*3//4),Rect(w//2,h//2,w//2+33,h//2+37)]
            s.select(regions[case_index]);window.capture_ui.overlay.refresh()
            report['display']=s.display.__dict__
            window.capture_ui.save();phase=2
        elif phase==2:
            s=runtime.workspace.capture
            if s.path:
                with Image.open(s.path) as image:
                    colors=image.convert('RGB').getextrema()
                    expected=baseline.crop((s.rect.left,s.rect.top,s.rect.right,s.rect.bottom))
                    difference=ImageChops.difference(image.convert('RGB'),expected).getbbox()
                    entry=dict(path=s.path,rect=s.rect.__dict__,size=list(image.size),rgb_extrema=colors,
                                  main_visible_after_restore=window.isVisible(),
                                  hide_ack_at_ms=s.hidden_at,worker_start_at_ms=s.started_at,
                                  pixel_difference_bounds=difference,
                                  own_ui_absent_by_exact_baseline_check=difference is None)
                    entry['status']='PASS' if image.size==(s.rect.width,s.rect.height) and difference is None else 'FAIL'
                    report['regions'].append(entry)
                if entry['status']!='PASS':return finish('PIXEL_OR_SIZE_MISMATCH')
                case_index+=1
                if case_index==10:report['status']='PASS';finish()
                else:phase=0
            elif s.error:finish(s.error)
    timer=QTimer();timer.timeout.connect(tick);timer.start(25)
    return app.exec()


if __name__=='__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
