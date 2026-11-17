from hand_v2.bootstrap import build_runtime
from hand_v2.adapters.timing import ManualClock
from hand_v2.domain.models import Activation,Gesture,GestureEvent


def test_practice_has_independent_fake_outputs_and_returns_waiting():
    r=build_runtime(clock=ManualClock(1000));r.controller.activate()
    assert r.enter_practice()
    p=r.practice_runtime
    assert p is not r and p.capture_worker is None and p.camera is None
    p.controller.activate();p.controller.neutral(True);p.scheduler.advance_to(1180)
    state=p.controller.state
    p.controller.handle(GestureEvent('e',Gesture.LEFT,('h',),1180,1180,state.context_version,state.camera_epoch))
    p.controller.flush_executor()
    assert p.keyboard.sent_chords==[('ALT','LEFT')]
    assert r.keyboard.sent_chords==[]
    assert r.controller.state.activation==Activation.WAITING
    assert not r.workspace.request_capture()
    r.exit_practice()
    assert r.practice_runtime is None and r.controller.state.activation==Activation.WAITING


def test_applying_settings_resets_candidates_and_preserves_stop():
    r=build_runtime(clock=ManualClock(1000));r.controller.activate();old=r.controller.state.context_version
    config=r.settings.copy();config['gestures']={**config['gestures'],'swipe_distance':.2,'smoothing_tau_ms':90}
    r.apply_settings(config)
    assert r.controller.state.context_version>old and not r.controller.state.ready
    assert r.vision.recognizer.motion.swipe_distance==.2
    r.controller.stop('button');r.apply_settings(config)
    assert r.controller.state.activation==Activation.WAITING
