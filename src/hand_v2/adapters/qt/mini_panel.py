import ctypes
from ctypes import wintypes

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from hand_v2.domain.models import Activation, ExecutionMode


class MiniPanel(QWidget):
    def __init__(self, controller, open_main):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.controller = controller
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle('HAND v2 상태')
        self.setFixedWidth(330)
        self.setStyleSheet('QWidget{background:#ffffff;color:#17342f;font:13px "Malgun Gothic";} QPushButton{padding:9px;border:1px solid #bddad3;border-radius:6px;}')
        layout=QVBoxLayout(self)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.last=QLabel('최근 실행: 없음');self.last.setWordWrap(True);layout.addWidget(self.last)
        row=QHBoxLayout()
        self.stop_button=QPushButton('중단');self.stop_button.clicked.connect(lambda:controller.stop('작은 상태창 중단'))
        self.continue_button=QPushButton('계속');self.continue_button.clicked.connect(controller.ack_confirmation)
        self.main_button=QPushButton('메인 열기');self.main_button.clicked.connect(open_main)
        for button in (self.stop_button,self.continue_button,self.main_button):
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus);row.addWidget(button)
        layout.addLayout(row)
        self.render_state(controller.state)

    def render_state(self, state):
        self.status.setText('HAND · '+('제어 중' if state.activation==Activation.ACTIVE else '대기')+
                            (' · 확인 후 계속' if state.confirmation_pending else '')+
                            (' · '+', '.join(sorted(state.blocked_reasons)) if state.blocked_reasons else ''))
        self.continue_button.setEnabled(state.confirmation_pending)
        if state.last_execution:
            self.last.setText('최근 실행: '+state.last_execution.status.value+' · '+state.last_execution.reason)

    def showEvent(self,event):
        if self.controller.state.execution_mode==ExecutionMode.REAL:
            from hand_v2.adapters.windows.native import bind
            user=ctypes.WinDLL('user32',use_last_error=True)
            get_style=bind(user,'GetWindowLongPtrW',[wintypes.HWND,ctypes.c_int],ctypes.c_ssize_t)
            set_style=bind(user,'SetWindowLongPtrW',[wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t],ctypes.c_ssize_t)
            hwnd=int(self.winId())
            set_style(hwnd,-20,get_style(hwnd,-20) | 0x08000000 | 0x00000080)  # NOACTIVATE, TOOLWINDOW
        super().showEvent(event)

    def nativeEvent(self,event_type,message):
        msg=wintypes.MSG.from_address(int(message))
        if msg.message==0x0021:  # WM_MOUSEACTIVATE: allow the click without activating.
            return True,3  # MA_NOACTIVATE
        return super().nativeEvent(event_type,message)
