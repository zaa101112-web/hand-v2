"""Actual Qt app and actual camera; diagnostic state only, no image recording or fake gestures."""
import argparse,json,multiprocessing,sys
from dataclasses import asdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--camera',type=int,default=1);p.add_argument('--seconds',type=int,default=180)
    args=p.parse_args()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from hand_v2.bootstrap import build_runtime
    from hand_v2.adapters.qt.window import MainWindow
    app=QApplication([]);runtime=build_runtime('WINDOWS_REAL');window=MainWindow(runtime)
    window.camera_combo.setCurrentIndex(args.camera);window.show()
    output=ROOT/'docs/validation/m03-live-app.json'
    def snapshot():
        state=asdict(runtime.controller.state)
        data={'state':state,'fps':runtime.camera_fps,'recognized_events':[asdict(e) for e in runtime.vision.recognized_events],
              'camera_stop':asdict(runtime.camera.last_stop) if runtime.camera.last_stop else None,
              'hotkey_registered':bool(window.hotkey and window.hotkey.registered),'raw_images_saved':False}
        output.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=lambda o:sorted(o) if isinstance(o,frozenset) else str(o)),encoding='utf-8')
    timer=QTimer();timer.timeout.connect(snapshot);timer.start(500)
    QTimer.singleShot(500,lambda:runtime.start_camera(args.camera,True))
    QTimer.singleShot(args.seconds*1000,window.close)
    result=app.exec();snapshot()
    return result if window.shutdown_ok else 2


if __name__=='__main__':
    multiprocessing.freeze_support()
    raise SystemExit(main())
