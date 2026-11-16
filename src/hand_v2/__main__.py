import argparse
import json
import sys


def main():
    parser=argparse.ArgumentParser(description="HAND v2 gesture-to-shortcut controller")
    parser.add_argument("--mode",choices=["DEV_SIMULATED","REPLAY","WINDOWS_REAL"],default="DEV_SIMULATED")
    parser.add_argument("--replay",help="CONTROL fixture directory; no OS input")
    parser.add_argument("--smoke",action="store_true",help="Start Qt, verify initial state, then exit")
    args=parser.parse_args()
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
    window.show()
    if args.smoke:
        QTimer.singleShot(250,window.close)
        QTimer.singleShot(350,app.quit)
    return app.exec()


if __name__=="__main__":
    raise SystemExit(main())
