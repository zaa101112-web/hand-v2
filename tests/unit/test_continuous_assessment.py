from hand_v2.domain.assessment import ContinuousAssessment, Trial
from hand_v2.domain.models import Gesture


def session():
    a=ContinuousAssessment('SYNTHETIC_LANDMARKS',(
        Trial('뒤로',Gesture.LEFT,1),Trial('확대',Gesture.ZOOM_IN,2)),trial_ms=1000,warmup_ms=300)
    a.start(1000)
    return a


def test_trial_denominator_and_misses_are_fixed_even_without_camera_frames():
    a=session()
    a.observe(1200,Gesture.START,True)  # Warmup is outside the scored tasks.
    a.observe(1500,Gesture.LEFT,True)
    a.tick(3300)
    report=a.report()
    assert report['complete'] and report['expected']==3
    assert report['recognized']==1 and report['missed']==2
    assert report['recognition_rate']==1/3
    assert report['source']=='SYNTHETIC_LANDMARKS'


def test_wrong_duplicate_and_blocked_are_not_reported_as_success():
    a=session()
    a.observe(1400,Gesture.LEFT,False)
    a.observe(1500,Gesture.RIGHT,True)
    a.observe(1600,Gesture.LEFT,True)
    a.observe(2400,Gesture.ZOOM_IN,True)
    a.observe(2450,Gesture.ZOOM_IN,True)
    a.tick(3300)
    report=a.report()
    assert report['wrong']==1 and report['duplicates']==1
    assert report['blocked_or_failed']==1 and report['executed']==2
    assert report['recognition_rate']==1 and report['execution_rate']==2/3
    assert report['passed'] is False


def test_boundary_belongs_to_next_trial_and_incomplete_rate_is_not_final():
    a=session();a.observe(2300,Gesture.LEFT,True)
    report=a.report()
    assert not report['complete'] and report['recognition_rate'] is None
    a.tick(3300)
    assert a.report()['wrong']==1 and a.report()['missed']==3


def test_demo_or_camera_failure_invalidates_accuracy():
    a=session();a.observe(1500,Gesture.LEFT,True)
    a.invalidate('DEMO_INPUT');a.tick(3300)
    assert not a.report()['valid']
    assert a.report()['recognition_rate'] is None
    assert a.report()['invalid_reason']=='DEMO_INPUT'


def test_perfect_sequence_counts_each_zoom_step_and_finishes_once():
    a=session()
    for at,g in ((1400,Gesture.LEFT),(2400,Gesture.ZOOM_IN),(2700,Gesture.ZOOM_IN)):
        a.observe(at,g,True)
    a.tick(3300);before=a.report();a.observe(3400,Gesture.LEFT,True)
    assert a.report()==before
    assert before['passed'] and before['execution_rate']==1


def test_frame_capture_time_can_precede_ui_tick_without_losing_measurement():
    a=session();a.tick(1510);a.observe(1500,Gesture.LEFT,True);a.tick(3300)
    assert a.report()['recognized']==1
