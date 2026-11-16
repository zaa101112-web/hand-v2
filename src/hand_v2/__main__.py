import argparse
import json
import sys


def main():
    parser=argparse.ArgumentParser(description="HAND v2 gesture-to-shortcut controller")
    parser.add_argument("--mode",choices=["DEV_SIMULATED","REPLAY","WINDOWS_REAL"],default="WINDOWS_REAL")
    parser.add_argument("--replay",help="CONTROL fixture directory; no OS input")
    parser.add_argument("--smoke",action="store_true",help="Start Qt, verify initial state, then exit")
    parser.add_argument('--smoke-report',help='Write startup/resource diagnostics after an offscreen smoke test')
    parser.add_argument('--camera',type=int,default=0,choices=range(4),help='Initial camera selection; camera stays off until requested')
    parser.add_argument('--camera-probe-report',help='Explicitly test the real camera/model without OS input and write JSON')
    args=parser.parse_args()
    if args.camera_probe_report:
        from pathlib import Path
        from hand_v2.adapters.vision.probe import probe_camera
        report=probe_camera(args.camera)
        report['frozen']=bool(getattr(sys,'frozen',False))
        Path(args.camera_probe_report).write_text(json.dumps(report,indent=2),encoding='utf-8')
        return 0 if report['success'] else 1
    if args.replay:
        from hand_v2.adapters.replay import run_fixture
        print(json.dumps(run_fixture(args.replay),ensure_ascii=False,indent=2))
        return 0
    if args.mode=="REPLAY":parser.error("--replay is required for REPLAY")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from hand_v2.bootstrap import build_runtime
    from hand_v2.adapters.qt.window import MainWindow
    app=QApplication(sys.argv[:1])
    runtime=build_runtime(args.mode)
    window=MainWindow(runtime)
    window.camera_combo.setCurrentIndex(args.camera)
    window.show()
    if args.smoke:
        QTimer.singleShot(250,window.close)
        QTimer.singleShot(350,app.quit)
    result=app.exec()
    exit_code=result if window.shutdown_ok else 2
    if args.smoke_report:
        from pathlib import Path
        from hand_v2.adapters.resources import verify_bundle
        import cv2
        import mediapipe
        import numpy
        import mss
        report=verify_bundle()
        report.update({'exit_code':exit_code,'mode':args.mode,'shutdown_ok':window.shutdown_ok,
                       'cv2':cv2.__version__,'mediapipe':mediapipe.__version__,'numpy':numpy.__version__,
                       'mss':mss.__version__,'camera_tested':False,'input_effect_tested':False})
        Path(args.smoke_report).write_text(json.dumps(report,indent=2),encoding='utf-8')
    return exit_code


if __name__=="__main__":
    from multiprocessing import freeze_support
    freeze_support()
    raise SystemExit(main())
