"""V2-T26/27/29: completion after STOP, worker ownership, display boundaries."""
from threading import Event
from hand_v2.adapters.jobs import LatestJob
from hand_v2.bootstrap import build_runtime
from hand_v2.domain.capture import Display,Rect
from hand_v2.domain.models import Activation,Mode
from hand_v2.adapters.timing import ManualClock
from hand_v2.adapters.qt.window import MainWindow


def test_only_latest_image_generation_is_delivered(qtbot):
    entered=Event();release=Event()
    def load(value):
        if value=='old':entered.set();release.wait(2)
        return value
    worker=LatestJob(load);worker.submit('old');assert entered.wait(1)
    worker.submit('discard');worker.submit('latest');release.set()
    results=[]
    qtbot.waitUntil(lambda: bool(results.extend(worker.poll()) or results),timeout=2000)
    assert results==[('latest','')]
    worker.close();assert worker.poll()==[]


def test_late_saved_file_after_stop_is_reported_without_reopening():
    r=build_runtime(clock=ManualClock(1000));r.controller.activate();r.workspace.request_capture()
    s=r.workspace.open_capture(Display('test',0,0,800,600,1));s.confirm('save',1000)
    s.ack_hidden(s.session_id,'save',s.context,1000);s.start(1100)
    r.controller.stop('F8');r.workspace.tick()
    assert s.closed and s.worker_running
    assert not r.workspace.request_capture()
    r.workspace.capture_result(s.session_id,'save',path='existing-result.png')
    assert 'existing-result.png' in r.workspace.notice
    assert s.closed and r.controller.state.mode==Mode.BROWSER
    assert r.controller.state.activation==Activation.WAITING


def test_shutdown_waits_for_capture_and_bounds_owned_worker(qtbot):
    class Worker:
        busy=True
        aborted=False
        def poll(self):return []
        def abort(self):self.aborted=True;self.busy=False;return True
    r=build_runtime(clock=ManualClock(1000));r.capture_worker=Worker()
    w=MainWindow(r);qtbot.addWidget(w);w.show();w.close()
    assert w.isVisible() and w._closing
    r.clock.advance_to(6000);w._tick()
    assert r.capture_worker.aborted and not w.shutdown_ok


def test_display_mapping_all_edges_at_three_scales():
    for scale in (1.,1.25,1.5):
        d=Display('test',-1920,0,1920,1080,scale)
        for r in (Rect(0,0,1920,1080),Rect(0,0,32,32),Rect(1888,0,1920,32),
                  Rect(0,1048,32,1080),Rect(1888,1048,1920,1080),Rect(120,120,900,600),
                  Rect(1,1,33,33),Rect(16,16,48,48),Rect(0,0,1900,1000),Rect(100,100,132,132)):
            converted=d.physical(r.left/scale,r.top/scale,r.right/scale,r.bottom/scale)
            assert abs(converted.width-r.width)<=2 and abs(converted.height-r.height)<=2
            assert converted.left<=r.left and converted.right>=r.right
