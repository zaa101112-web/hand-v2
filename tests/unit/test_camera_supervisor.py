from dataclasses import dataclass
from hand_v2.adapters.timing import ManualClock
from hand_v2.adapters.vision.supervisor import CameraSupervisor


class FakeSession:
    def __init__(self, epoch):
        self.epoch=epoch;self.alive=True;self.stops=0;self.terminates=0;self.kills=0;self.closed=False
        self.last_heartbeat_ms=1000;self.preview=True;self.messages=[]
    def is_alive(self):return self.alive
    def request_stop(self):self.stops+=1
    def terminate(self):self.terminates+=1
    def kill(self):self.kills+=1;self.alive=False
    def close(self):self.closed=True
    def drain(self):result=self.messages;self.messages=[];return result
    def set_preview(self,value):self.preview=value


def rig():
    clock=ManualClock(1000);sessions=[]
    def factory(epoch,index,preview):
        session=FakeSession(epoch);session.preview=preview;sessions.append(session);return session
    return clock,sessions,CameraSupervisor(clock,factory)


def test_start_is_idempotent_and_restart_changes_epoch():
    clock,sessions,supervisor=rig()
    assert supervisor.start(0)
    assert not supervisor.start(0)
    assert supervisor.epoch==1 and len(sessions)==1
    supervisor.stop();supervisor.stop()
    assert sessions[0].stops==1
    sessions[0].alive=False
    supervisor.poll()
    assert sessions[0].closed and supervisor.status=='STOPPED'
    assert supervisor.start(1)
    assert supervisor.epoch==2 and len(sessions)==2


def test_hung_camera_read_or_release_does_not_block_ui_poll_and_is_bounded():
    clock,sessions,supervisor=rig();supervisor.start(0);supervisor.stop()
    clock.advance_to(2999);supervisor.poll();assert sessions[0].terminates==0
    clock.advance_to(3000);supervisor.poll();assert sessions[0].terminates==1
    clock.advance_to(4000);supervisor.poll();assert sessions[0].kills==1
    supervisor.poll()
    assert supervisor.status=='STOPPED' and supervisor.last_stop.forced
    assert supervisor.last_stop.elapsed_ms<=4000 and supervisor.last_stop.success


def test_heartbeat_loss_reports_failure_and_stops_owned_session():
    clock,sessions,supervisor=rig();supervisor.start(0)
    sessions[0].messages=[('ready',None)]
    supervisor.poll()
    clock.advance_to(2001)
    events=supervisor.poll()
    assert any(kind=='error' and reason=='CAMERA_STALLED' for kind,reason in events)
    assert sessions[0].stops==1 and supervisor.status=='STOPPING'


def test_child_death_reports_error_without_claiming_connected():
    _,sessions,supervisor=rig();supervisor.start(0);sessions[0].alive=False
    assert ('error','CAMERA_PROCESS_EXITED') in supervisor.poll()
    assert sessions[0].closed and supervisor.status=='FAILED'


def test_startup_budget_and_preview_toggle():
    clock,sessions,supervisor=rig();supervisor.start(0,preview=False)
    assert not sessions[0].preview
    supervisor.set_preview(True);assert sessions[0].preview
    clock.advance_to(10999);assert supervisor.poll()==[]
    clock.advance_to(11000)
    assert ('error','CAMERA_START_TIMEOUT') in supervisor.poll()
