from hand_v2.bootstrap import build_runtime
from hand_v2.domain.models import Result,Status,Action

# V2-T17/V2-T40: ERROR-only diagnostics must retain real camera/input failures.


def test_execution_failures_are_error_level_not_filtered_as_info():
    class Sink:
        def __init__(self):self.rows=[]
        def record(self,kind,**fields):self.rows.append((kind,fields))
    sink=Sink();r=build_runtime(events=sink)
    r.controller.on_execution_result(Result('failed',r.controller.state.context_version,r.clock.now_ms(),Status.FAILED,'SENDINPUT_PARTIAL'),Action.BACK)
    failure=next(fields for kind,fields in sink.rows if kind=='command' and fields['status']==Status.FAILED)
    assert failure.get('level')=='ERROR'


def test_failed_key_release_has_an_error_diagnostic():
    from hand_v2.domain.models import ReleaseResult
    class Sink:
        def __init__(self):self.rows=[]
        def record(self,kind,**fields):self.rows.append((kind,fields))
    sink=Sink();r=build_runtime(events=sink);r.keyboard.auto_release=False;r.controller.request_release()
    request=r.keyboard.release_requests[-1]
    r.controller.on_release_result(ReleaseResult(request,False,r.clock.now_ms()))
    assert any(kind=='release' and fields.get('level')=='ERROR' for kind,fields in sink.rows)


def test_camera_errors_are_logged_but_normal_camera_off_is_not_an_error():
    class Sink:
        def __init__(self):self.rows=[]
        def record(self,kind,**fields):self.rows.append((kind,fields))
    sink=Sink();r=build_runtime(events=sink)
    r.controller.camera_failed('CAMERA_OFF')
    assert not any(kind=='camera' and fields.get('level')=='ERROR' for kind,fields in sink.rows)
    r.controller.camera_failed('CAMERA_READ_FAILED')
    assert any(kind=='camera' and fields.get('level')=='ERROR' and fields.get('reason')=='CAMERA_READ_FAILED'
               for kind,fields in sink.rows)
