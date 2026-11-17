"""Bounded shutdown watchdog; not a claim to recover native/GIL deadlocks."""
from threading import Thread,Event
import os


class ShutdownWatchdog:
    def __init__(self,cleanup,exit_process=os._exit):
        self.cleanup=cleanup;self.exit_process=exit_process;self.cancelled=Event()
        self.thread=None;self.triggered=False

    def arm(self,seconds=10):
        if self.thread is not None:return
        def watch():
            reserve=min(1,seconds/10)
            if self.cancelled.wait(seconds-reserve):return
            self.triggered=True
            def clean():
                try:self.cleanup()
                except Exception:pass  # Forced exit must not be replaced by an exception.
            worker=Thread(target=clean,name='HAND-emergency-cleanup',daemon=True)
            worker.start();worker.join(reserve)
            self.exit_process(2)
        self.thread=Thread(target=watch,name='HAND-shutdown-watchdog',daemon=True);self.thread.start()

    def cancel(self):self.cancelled.set()


def write_shutdown_report(folder,details):
    from pathlib import Path
    import json
    from datetime import datetime,timezone
    path=Path(folder)/'last-shutdown.json';path.parent.mkdir(parents=True,exist_ok=True)
    details={'utc':datetime.now(timezone.utc).isoformat(),**details}
    with path.open('w',encoding='utf-8') as stream:
        json.dump(details,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
