"""Screen and file effects are created/owned by one isolated capture process."""
from dataclasses import asdict
import multiprocessing as mp
from queue import Empty
from pathlib import Path
import os,uuid


def display_matches(display, monitors):
    return any((m['left'],m['top'],m['width'],m['height'])==
               (display.left,display.top,display.width,display.height) for m in monitors)


def capture_worker(result_queue, session, attempt, display, rect, folder,temporary_path):
    try:
        import mss
        from PIL import Image
        from .capture_files import atomic_png
        with mss.mss() as screen:
            if not display_matches(display,screen.monitors[1:]):raise ValueError('DISPLAY_CHANGED')
            from .windows.display import physical_display
            current=physical_display(display.name,None)
            if current is not None and current!=display:raise ValueError('DISPLAY_CHANGED')
            shot=screen.grab({'left':display.left+rect.left,'top':display.top+rect.top,
                              'width':rect.width,'height':rect.height})
            path=atomic_png(Image.frombytes('RGB',shot.size,shot.rgb),folder,temporary_path=temporary_path)
        result_queue.put((session,attempt,str(path),'',asdict(display)))
    except Exception as exc:
        result_queue.put((session,attempt,'',f'{type(exc).__name__}: {exc}',asdict(display)))


class CaptureWorker:
    def __init__(self):
        self.context=mp.get_context('spawn');self.process=None;self.queue=None
        self.request=None;self.received=False
        self.temporary_path=None

    @property
    def busy(self):return self.process is not None

    def start(self, session, folder):
        if self.busy:return False
        self.queue=self.context.Queue();self.received=False
        self.request=(session.session_id,session.attempt,session.display)
        self.temporary_path=Path(folder).resolve()/('.hand-capture-'+uuid.uuid4().hex+'.tmp')
        self.process=self.context.Process(target=capture_worker,args=(self.queue,session.session_id,
            session.attempt,session.display,session.rect,str(folder),str(self.temporary_path)),name='HAND-capture',daemon=True)
        try:self.process.start()
        except Exception:
            self.process=None;self.queue.close();self.queue=None;raise
        return True

    def poll(self):
        results=[]
        if self.process is None:return results
        try:
            value=self.queue.get_nowait();results.append(value);self.received=True
        except Empty:pass
        if not self.process.is_alive():
            self.process.join()
            if not self.received:
                try:results.append(self.queue.get(timeout=.05));self.received=True
                except Empty:
                    session,attempt,display=self.request
                    results.append((session,attempt,'','CAPTURE_WORKER_EXIT',asdict(display)))
            self.process.close();self.process=None;self.queue.close();self.queue=None
        return results

    def abort(self):
        if self.process:
            self.process.terminate();self.process.join(timeout=.5)
            if self.process.is_alive():return False
            self.process.close();self.process=None
        if self.queue:self.queue.close();self.queue=None
        if self.temporary_path:
            try:self.temporary_path.unlink(missing_ok=True)
            except OSError:return False
        return True


def default_capture_folder():
    # Windows Known Folder respects relocation/OneDrive instead of assuming ~/Pictures.
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class GUID(ctypes.Structure):
            _fields_=[('Data1',wintypes.DWORD),('Data2',wintypes.WORD),('Data3',wintypes.WORD),('Data4',ctypes.c_ubyte*8)]
        import uuid
        guid=GUID.from_buffer_copy(uuid.UUID('33e28130-4e1e-4676-835a-98395c3bc3bb').bytes_le)
        pointer=ctypes.c_wchar_p()
        result=ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid),0,None,ctypes.byref(pointer))
        if result==0:
            try:return Path(pointer.value)/'HAND-v2'
            finally:ctypes.windll.ole32.CoTaskMemFree(pointer)
    return Path.home()/'Pictures'/'HAND-v2'
