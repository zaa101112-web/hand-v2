from dataclasses import dataclass
from math import floor, ceil


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self): return self.right-self.left
    @property
    def height(self): return self.bottom-self.top
    @property
    def valid(self): return self.width >= 32 and self.height >= 32


@dataclass(frozen=True)
class Display:
    name: str
    left: int
    top: int
    width: int
    height: int
    scale: float

    def physical(self, left, top, right, bottom):
        return Rect(max(0,min(self.width,floor(left*self.scale))),
                    max(0,min(self.height,floor(top*self.scale))),
                    max(0,min(self.width,ceil(right*self.scale))),
                    max(0,min(self.height,ceil(bottom*self.scale))))


class CaptureSession:
    """Pure session/attempt state. Worker results remain factual after cancellation."""
    def __init__(self, session_id, context, previous_mode, display):
        self.session_id, self.context = session_id, context
        self.previous_mode, self.display = previous_mode, display
        w,h=display.width,display.height
        self.rect=Rect(w//4,h//4,w*3//4,h*3//4)
        self.phase='SELECTING'
        self.attempt=None
        self.confirmed_at=None
        self.hidden_at=None
        self.started_at=None
        self.worker_running=False
        self.closed=False
        self.path=''
        self.error=''
        self.slow=False

    def select(self, rect):
        if self.closed or self.phase == 'SAVING': return False
        d=self.display
        if not (0<=rect.left<=rect.right<=d.width and 0<=rect.top<=rect.bottom<=d.height): return False
        self.rect=rect
        self.phase='READY' if rect.valid else 'SELECTING'
        self.error=''
        return True

    def fullscreen(self):
        self.select(Rect(0,0,self.display.width,self.display.height))

    def adjust(self, dx, dy, resize=False):
        r,d=self.rect,self.display
        if resize:
            return self.select(Rect(r.left,r.top,max(r.left,min(d.width,r.right+dx)),max(r.top,min(d.height,r.bottom+dy))))
        dx=max(-r.left,min(d.width-r.right,dx));dy=max(-r.top,min(d.height-r.bottom,dy))
        return self.select(Rect(r.left+dx,r.top+dy,r.right+dx,r.bottom+dy))

    def confirm(self, attempt, now):
        if self.closed or self.worker_running or self.phase=='SAVING' or not self.rect.valid:return False
        self.attempt=attempt;self.confirmed_at=now;self.hidden_at=None;self.started_at=None
        self.phase='SAVING';self.error='';self.slow=False
        return True

    def ack_hidden(self, session, attempt, context, now):
        if self.closed or self.phase!='SAVING' or (session,attempt,context)!=(self.session_id,self.attempt,self.context):return False
        if self.hidden_at is not None or now-self.confirmed_at>=1000:return False
        self.hidden_at=now
        return True

    def can_start(self, now):
        return (not self.closed and self.phase=='SAVING' and not self.worker_running
                and self.started_at is None and self.hidden_at is not None and now-self.hidden_at>=100)

    def start(self, now):
        if not self.can_start(now):return False
        self.worker_running=True;self.started_at=now
        return True

    def tick(self, now):
        if self.closed:return None
        if self.phase=='SAVING' and self.hidden_at is None and now-self.confirmed_at>=1000:
            self.phase='ERROR';self.error='HIDE_TIMEOUT';return self.error
        if self.worker_running:
            if now-self.started_at>=10000:
                self.cancel();self.error='CAPTURE_STALLED';return self.error
            if now-self.started_at>=5000 and not self.slow:
                self.slow=True;return 'SLOW'
        return None

    def cancel(self):
        self.closed=True
        self.phase='CLOSED'

    def finish(self, session, attempt, path='', error=''):
        if (session,attempt)!=(self.session_id,self.attempt) or not self.worker_running:return False
        self.worker_running=False;self.path=path;self.error=error
        if path:self.cancel()
        elif not self.closed:self.phase='ERROR'
        return True
