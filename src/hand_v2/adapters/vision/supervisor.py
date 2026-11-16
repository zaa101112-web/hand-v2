from dataclasses import dataclass


@dataclass(frozen=True)
class CameraStopResult:
    success: bool
    forced: bool
    elapsed_ms: int


class CameraSupervisor:
    """Main-thread nonblocking lifecycle. All native camera calls belong to the child."""
    def __init__(self, clock, session_factory=None):
        self.clock=clock
        self.factory=session_factory
        self.session=None
        self.epoch=0
        self.status='STOPPED'
        self.last_stop=None
        self._stopping_at=None
        self._terminated=False
        self._killed=False

    def start(self,index=0,preview=True):
        if self.session is not None:return False
        self.epoch+=1
        if self.factory is None:
            from .process import SpawnSession
            factory=SpawnSession
        else:factory=self.factory
        self._started_at=self.clock.now_ms()
        self._stopping_at=None
        self._terminated=self._killed=False
        self.last_stop=None
        self.status='STARTING'
        try:self.session=factory(self.epoch,index,preview)
        except Exception:
            self.status='FAILED'
            raise
        return True

    def set_preview(self,value):
        if self.session:self.session.set_preview(value)

    def stop(self):
        if not self.session or self._stopping_at is not None:return
        self._stopping_at=self.clock.now_ms()
        self.status='STOPPING'
        self.session.request_stop()

    def poll(self):
        if not self.session:return []
        now=self.clock.now_ms()
        if self._stopping_at is not None:
            elapsed=now-self._stopping_at
            if not self.session.is_alive():
                self.session.close();self.session=None;self.status='STOPPED'
                self.last_stop=CameraStopResult(True,self._terminated or self._killed,elapsed)
                return [('stopped',self.last_stop)]
            if elapsed>=2000 and not self._terminated:
                self.session.terminate();self._terminated=True
            if elapsed>=3000 and not self._killed:
                self.session.kill();self._killed=True
            if elapsed>=4000 and self.session.is_alive():
                self.status='FAILED'
                self.last_stop=CameraStopResult(False,True,elapsed)
                return [('error','CAMERA_STOP_TIMEOUT')]
            return []
        events=self.session.drain()
        if any(kind=='ready' for kind,_ in events):self.status='CONNECTED'
        if not self.session.is_alive():
            self.session.close();self.session=None;self.status='FAILED'
            return [*events,('error','CAMERA_PROCESS_EXITED')]
        if any(kind=='error' for kind,_ in events):
            self.stop();return events
        if self.status=='STARTING' and now-self._started_at>=10000:
            self.stop();return [*events,('error','CAMERA_START_TIMEOUT')]
        if self.status=='CONNECTED' and now-self.session.last_heartbeat_ms>1000:
            self.stop();return [*events,('error','CAMERA_STALLED')]
        return events
