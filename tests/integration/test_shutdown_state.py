from hand_v2.bootstrap import build_runtime
from hand_v2.domain.models import ExecutionMode


def test_shutdown_consumes_release_ack_before_final_diagnostics():
    runtime=build_runtime(ExecutionMode.REAL)
    runtime.controller.stop('앱 종료')
    assert runtime.close()
    assert not runtime.controller.state.release_pending
    assert not runtime.controller.state.keyboard_state.owned_keys
