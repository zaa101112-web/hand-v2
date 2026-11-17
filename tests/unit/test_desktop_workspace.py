from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.timing import ManualClock
from hand_v2.domain.models import Mode, Activation, Action, Command, Status
from hand_v2.domain.images import ImageAsset
from hand_v2.domain.capture import Display


def test_image_actions_share_use_case_without_keyboard_output():
    r=build_runtime(clock=ManualClock(1000));r.controller.set_mode(Mode.IMAGE)
    r.workspace.gallery.replace([ImageAsset('a',1,1,b''),ImageAsset('b',1,1,b'')])
    cmd=Command('c','e',Action.NEXT_IMAGE,'APP',r.controller.state.context_version,1000,1250)
    assert r.controller.app_actions.execute(cmd).status==Status.APPLIED
    assert r.workspace.gallery.index==1 and r.keyboard.sent_chords==[]
    r.controller.set_mode(Mode.BROWSER)
    assert not r.workspace.image_action(Action.PREV_IMAGE)


def test_capture_waits_for_release_and_stop_never_restores_active():
    r=build_runtime(clock=ManualClock(1000));c=r.controller
    c.activate()
    assert r.workspace.request_capture()
    assert c.state.mode==Mode.CAPTURE and not c.state.ready
    s=r.workspace.open_capture(Display('x',0,0,100,100,1))
    assert s is not None
    c.stop('F8');r.workspace.tick()
    assert s.closed and c.state.mode==Mode.BROWSER
    assert c.state.activation==Activation.WAITING
    assert not r.workspace.request_capture() if s.worker_running else True


def test_capture_cancel_without_stop_preserves_latest_activation():
    r=build_runtime(clock=ManualClock(1000));r.controller.activate()
    r.workspace.request_capture();s=r.workspace.open_capture(Display('x',0,0,100,100,1))
    r.workspace.cancel_capture()
    assert s.closed and r.controller.state.activation==Activation.ACTIVE
    assert not r.controller.state.ready
