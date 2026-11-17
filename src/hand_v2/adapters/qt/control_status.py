from hand_v2.domain.models import Activation


def control_status(state):
    if state.activation!=Activation.ACTIVE:return '제어 대기 · V로 시작하세요'
    if state.blocked_reasons or state.release_pending:return '제어 보류 · 상태를 확인하세요'
    if state.confirmation_pending:return '확인 창을 닫고 계속을 누르세요'
    if state.dialog_lock:return '열린 창에서 작업을 마쳐주세요'
    if state.ready:return '제어 중 · 동작 가능'
    return '제어 중 · 손을 펼쳐 준비하세요'
