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
    from PIL import Image
    from hand_v2.bootstrap import build_runtime
    from hand_v2.domain.models import ExecutionMode
    from hand_v2.domain.capture import Rect
    from hand_v2.adapters.qt.window import MainWindow
    app=QApplication([])
    background=QWidget();background.setWindowTitle('HAND capture QA — controlled solid background')
    background.setStyleSheet('background:rgb(211,31,91);');background.showFullScreen()
    runtime=build_runtime(ExecutionMode.REAL)
    runtime.capture_folder=ROOT/'.build-staging'/'capture-qa'
    window=MainWindow(runtime);window.show();window.raise_()
    report={'kind':'actual Windows screen capture; controlled pixels; production hide/save path', 'status':'RUNNING'}
    started=time.monotonic();phase=0
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
        nonlocal phase
        if time.monotonic()-started>25:return finish('TIMEOUT')
        if phase==0 and time.monotonic()-started>1:
            runtime.workspace.request_capture();phase=1
        elif phase==1 and window.capture_ui.overlay:
            s=runtime.workspace.capture
            # Interior pixels are covered by the real HAND UI/overlay before hiding.
            s.select(Rect(300,300,620,540));window.capture_ui.overlay.refresh()
            report['display']=s.display.__dict__;report['rect']=s.rect.__dict__
            window.capture_ui.save();phase=2
        elif phase==2:
            s=runtime.workspace.capture
            if s.path:
                with Image.open(s.path) as image:
                    colors=image.convert('RGB').getextrema()
                    report.update(path=s.path,size=list(image.size),rgb_extrema=colors,
                                  main_visible_after_restore=window.isVisible(),
                                  hide_ack_at_ms=s.hidden_at,worker_start_at_ms=s.started_at,
                                  own_ui_absent_by_exact_pixel_check=colors==((211,211),(31,31),(91,91)))
                    report['status']='PASS' if image.size==(320,240) and colors==((211,211),(31,31),(91,91)) else 'FAIL'
                finish()
            elif s.error:finish(s.error)
    timer=QTimer();timer.timeout.connect(tick);timer.start(25)
    return app.exec()


if __name__=='__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
