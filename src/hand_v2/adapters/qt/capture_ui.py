from PySide6.QtCore import QTimer
from hand_v2.domain.capture import Display
from .capture_overlay import CaptureOverlay


class CaptureUi:
    def __init__(self,window,runtime):
        self.window=window;self.runtime=runtime;self.workspace=runtime.workspace
        self.worker=runtime.capture_worker;self.overlay=None;self.screen=None
        self.hidden=False;self.was_main=False;self.was_mini=False

    def display(self):
        screen=self.screen or self.window.screen();geometry=screen.geometry();scale=screen.devicePixelRatio()
        from hand_v2.adapters.windows.display import physical_display
        return physical_display(screen.name(),scale) or Display(screen.name(),round(geometry.x()*scale),
            round(geometry.y()*scale),round(geometry.width()*scale),round(geometry.height()*scale),scale)

    def tick(self):
        w=self.workspace
        if self.worker:
            for session,attempt,path,error,snapshot in self.worker.poll():w.capture_result(session,attempt,path,error)
        if w.capture_pending and not self.runtime.controller.state.release_pending:
            self.screen=self.window.screen()
            session=w.open_capture(self.display())
            if session:
                self.overlay=CaptureOverlay(session,self.save,self.cancel,lambda:self.cancel(True))
                self.overlay.setGeometry(self.screen.geometry());self.overlay.show();self.overlay.activateWindow();self.overlay.setFocus()
        s=w.capture
        if not s:return
        if not s.closed and not s.worker_running and s.display!=self.display():
            self.runtime.controller.stop('화면 배율 또는 해상도 변경');w.cancel_capture();w.notice='화면 구성이 변경되어 캡처를 취소했습니다. 다시 시작하세요.'
        if s.can_start(self.runtime.clock.now_ms()):
            if self.worker and not self.worker.busy:
                s.start(self.runtime.clock.now_ms())
                try:self.worker.start(s,self.runtime.capture_folder)
                except Exception as exc:w.capture_result(s.session_id,s.attempt,error=type(exc).__name__)
            elif not self.worker:
                w.notice='시뮬레이션: 실제 화면 파일을 저장하지 않았습니다.';w.cancel_capture()
        if s.closed:
            if self.overlay:self.overlay.close();self.overlay.deleteLater();self.overlay=None
            self.restore()
        elif s.phase=='ERROR':
            self.restore()
            if self.overlay:self.overlay.show();self.overlay.refresh()
        if self.overlay:self.overlay.refresh()
        self.window.capture_notice.setText(w.notice)

    def save(self):
        s=self.workspace.capture
        if not s or (self.worker and self.worker.busy):return
        if not s.confirm(self.runtime.ids.next_id('capture-save'),self.runtime.clock.now_ms()):return
        self.was_main=self.window.isVisible();self.was_mini=self.window.mini_panel.isVisible()
        self.hidden=True
        self.window.hide();self.window.mini_panel.hide();self.overlay.hide()
        identity=(s.session_id,s.attempt,s.context)
        def acknowledge():
            if (not self.window.isVisible() and not self.window.mini_panel.isVisible()
                    and self.overlay and not self.overlay.isVisible()):
                s.ack_hidden(*identity,self.runtime.clock.now_ms())
        QTimer.singleShot(0,acknowledge)

    def restore(self):
        if not self.hidden:return
        self.hidden=False
        if self.was_main:self.window.show()
        if self.was_mini:self.window.mini_panel.show()

    def cancel(self,stop=False):
        if stop:self.runtime.controller.stop('캡처 Esc')
        self.workspace.cancel_capture()

    def close(self):
        self.workspace.cancel_capture()
        if self.overlay:self.overlay.close();self.overlay.deleteLater();self.overlay=None
        return not self.worker or not self.worker.busy
