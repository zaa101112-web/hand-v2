from hand_v2.domain.images import Gallery
from hand_v2.domain.capture import CaptureSession
from hand_v2.domain.models import Action, Mode, Result, Status


class DesktopWorkspace:
    def __init__(self, controller, clock, ids):
        self.controller,self.clock,self.ids=controller,clock,ids
        self.gallery=Gallery()
        self.capture=None
        self.capture_pending=False
        self.previous_mode=Mode.BROWSER
        self.capture_context=None
        self.notice=''
        self.practice=False

    def image_action(self, action):
        if self.controller.state.mode!=Mode.IMAGE or not self.gallery.current:return False
        if action==Action.PREV_IMAGE:self.gallery.move(-1)
        elif action==Action.NEXT_IMAGE:self.gallery.move(1)
        elif action==Action.ZOOM_IN:self.gallery.zoom(1.15)
        elif action==Action.ZOOM_OUT:self.gallery.zoom(1/1.15)
        elif action==Action.FIT_IMAGE:self.gallery.fit()
        else:return False
        return True

    def execute(self, command):
        accepted=self.request_capture() if command.action==Action.CAPTURE else self.image_action(command.action)
        return Result(command.command_id,self.controller.state.context_version,self.clock.now_ms(),
                      Status.APPLIED if accepted else Status.BLOCKED,
                      'CAPTURE_ACCEPTED' if accepted and command.action==Action.CAPTURE else
                      'IMAGE_APPLIED' if accepted else 'APP_ACTION_UNAVAILABLE')

    def request_capture(self):
        c=self.controller
        if self.practice or self.capture_pending or (self.capture and (not self.capture.closed or self.capture.worker_running)):
            return False
        if c.state.dialog_lock or c.state.confirmation_pending or c.state.phase!='RUNNING':return False
        self.previous_mode=c.state.mode
        self.capture_pending=True
        self.capture=None
        c.enter_capture()
        self.capture_context=c.state.context_version
        self.notice='입력 해제 확인 후 영역 선택을 엽니다.'
        return True

    def open_capture(self, display):
        if not self.capture_pending or self.controller.state.release_pending:return None
        if self.controller.state.context_version!=self.capture_context:return None
        self.capture=CaptureSession(self.ids.next_id('capture'),self.capture_context,self.previous_mode,display)
        self.capture_pending=False
        return self.capture

    def cancel_capture(self):
        self.capture_pending=False
        if self.capture:self.capture.cancel()
        self._restore()

    def _restore(self):
        if self.controller.state.mode==Mode.CAPTURE:self.controller.leave_capture(self.previous_mode)

    def tick(self):
        if (self.capture_pending or (self.capture and not self.capture.closed)) and self.controller.state.context_version!=self.capture_context:
            self.cancel_capture()
        if self.capture:
            event=self.capture.tick(self.clock.now_ms())
            if event=='CAPTURE_STALLED':
                self.controller.stop(event);self.notice='저장이 지연되어 제어를 중단했습니다. 작업 결과를 기다립니다.'
            elif event=='SLOW':self.notice='저장이 5초 이상 걸리고 있습니다. 중복 저장하지 않고 결과를 기다립니다.'
            elif event:self.notice=event
            if self.capture.closed:self._restore()

    def capture_result(self, session, attempt, path='', error=''):
        if not self.capture or not self.capture.finish(session,attempt,path,error):return False
        self.notice=f'저장 완료: {path}' if path else f'저장 실패: {error}. 다시 확인하면 현재 화면을 새로 저장합니다.'
        if self.capture.closed:self._restore()
        return True
