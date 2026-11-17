"""Single daemon worker, one replaceable pending image generation; no Qt in workers."""
from threading import Thread
from queue import Queue, Empty


class LatestJob:
    def __init__(self, operation):
        self.operation=operation;self.generation=0
        self.thread=None;self.pending=None;self.results=Queue();self.closed=False

    def submit(self, payload):
        self.generation+=1
        self.pending=(self.generation,payload)
        self._start()
        return self.generation

    def _start(self):
        if self.closed or self.pending is None or (self.thread and self.thread.is_alive()):return
        generation,payload=self.pending;self.pending=None
        def work():
            try:self.results.put((generation,self.operation(payload),''))
            except Exception as exc:self.results.put((generation,None,type(exc).__name__))
        self.thread=Thread(target=work,name='HAND-image-loader',daemon=True);self.thread.start()

    def poll(self):
        result=[]
        while True:
            try:
                generation,value,error=self.results.get_nowait()
                if generation==self.generation and not self.closed:result.append((value,error))
            except Empty:break
        self._start()
        return result

    def close(self):
        self.closed=True;self.pending=None;self.generation+=1
        return not self.thread or not self.thread.is_alive()

    @property
    def busy(self):return bool(self.thread and self.thread.is_alive())
