import time
import pytest
from hand_v2.adapters.timing import MonotonicClock
from hand_v2.adapters.vision.process import SpawnSession
from hand_v2.adapters.vision.supervisor import CameraSupervisor


def hanging_read(epoch,index,preview,stop,frames,status,heartbeat):
    heartbeat.value=time.monotonic_ns()//1_000_000
    status.put(('ready',None))
    time.sleep(60)


def hanging_release(epoch,index,preview,stop,frames,status,heartbeat):
    heartbeat.value=time.monotonic_ns()//1_000_000
    status.put(('ready',None))
    stop.wait(30)
    time.sleep(60)


@pytest.mark.parametrize('target',[hanging_read,hanging_release])
def test_owned_spawned_camera_is_terminated_without_freezing_parent(target):
    supervisor=CameraSupervisor(MonotonicClock(),lambda e,i,p:SpawnSession(e,i,p,child_target=target))
    supervisor.start(0)
    session=supervisor.session
    started=time.monotonic()
    try:
        while supervisor.status=='STARTING' and time.monotonic()-started<5:
            supervisor.poll();time.sleep(.01)
        assert supervisor.status=='CONNECTED'
        supervisor.stop();stopped=time.monotonic();polls=0
        while supervisor.session and time.monotonic()-stopped<4:
            supervisor.poll();polls+=1;time.sleep(.01)
        assert supervisor.session is None
        assert supervisor.last_stop.success and supervisor.last_stop.forced
        assert polls>10 and time.monotonic()-stopped<4
    finally:
        if supervisor.session:
            session.kill()
            session.process.join(1)
            session.close()
