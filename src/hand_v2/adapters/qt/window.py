from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QScrollArea, QComboBox)

from hand_v2.domain.models import Activation, ExecutionMode, Gesture, GestureEvent, Mode, Status
from .controller_bridge import ControllerBridge
from .fonts import ensure_readable_fonts


STYLE = """
QMainWindow, QWidget#Root {background:#f5f7fa;color:#172b3a;}
QWidget {font-family:'Segoe UI','Malgun Gothic';font-size:13px;color:#172b3a;}
QFrame#Header,QFrame#Sidebar {background:white;}
QFrame#Card {background:white;border:1px solid #dce5ec;border-radius:14px;}
QLabel {background:transparent;}
QLabel#Logo {color:#087f76;font-size:27px;font-weight:700;letter-spacing:3px;}
QLabel#Title {font-size:25px;font-weight:700;}
QLabel#Muted {color:#526579;font-size:12px;}
QLabel#Value {font-size:20px;font-weight:600;}
QLabel#Banner {background:#fff7e7;color:#815519;border:1px solid #ead8b4;border-radius:8px;padding:10px;}
QPushButton {background:white;border:1px solid #dce5ec;border-radius:8px;padding:10px 13px;min-height:18px;}
QPushButton:hover {background:#eef6f3;border-color:#91c3b8;}
QPushButton:focus {border:2px solid #087f76;}
QPushButton:checked {background:#e8f4f1;color:#087f76;border-color:#087f76;}
QPushButton#Primary {background:#087f76;color:white;border-color:#087f76;font-weight:600;}
QPushButton#Stop {background:#fff7f7;color:#a53737;border-color:#e7caca;}
QPushButton#Nav {text-align:left;border:none;padding:13px;}
QComboBox {background:white;border:1px solid #dce5ec;border-radius:7px;padding:8px;}
QScrollArea {border:none;background:transparent;}
"""


def label(text, name="", wrap=True):
    w = QLabel(text)
    w.setWordWrap(wrap)
    w.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        w.setObjectName(name)
    return w


def button(text, callback, name=""):
    w = QPushButton(text)
    w.setObjectName(name)
    w.setAccessibleName(text)
    w.clicked.connect(callback)
    return w


def card():
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20,20,20,20)
    layout.setSpacing(12)
    return frame, layout


class MainWindow(QMainWindow):
    def __init__(self, runtime):
        super().__init__()
        ensure_readable_fonts()
        self.runtime = runtime
        self.controller = runtime.controller
        self.setWindowTitle("HAND v2 — 손동작 단축키 제어")
        self.resize(1280,860)
        self.setMinimumSize(960,720)
        self.setStyleSheet(STYLE)
        self._build()
        self.hotkey=None
        self.shutdown_ok=True
        from .mini_panel import MiniPanel
        self.mini_panel=MiniPanel(self.controller,self.open_main)
        if runtime.controller.state.execution_mode==ExecutionMode.REAL:
            from hand_v2.adapters.windows.hotkey import GlobalStopHotkey
            self.hotkey=GlobalStopHotkey(int(self.winId()),lambda:self.controller.stop('전역 F8'),runtime.foreground.native)
            self.banner.setText('Windows 실제 입력 모드 · 카메라 연결은 다음 단계입니다. '+
                                ('전역 F8 중단 사용 가능' if self.hotkey.registered else 'F8 등록 실패 · 중단 버튼/숫자 3을 사용하세요'))
        self.bridge = ControllerBridge(self)
        self.bridge.state_changed.connect(self.render_state)
        runtime.ui.listener = self.bridge.render_state
        self.render_state(self.controller.state)
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.escape = QShortcut(QKeySequence("Escape"),self)
        self.escape.activated.connect(lambda:self.controller.stop("Esc"))

    def _build(self):
        root = QWidget(); root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        header = QFrame();header.setObjectName("Header")
        head = QHBoxLayout(header);head.setContentsMargins(25,17,25,17)
        head.addWidget(label("HAND","Logo"));head.addWidget(label("손동작 단축키 제어","Muted"));head.addStretch()
        self.state_label = label("제어 대기");head.addWidget(self.state_label)
        self.stop_button = button("중단",lambda:self.controller.stop("중단 버튼"),"Stop");head.addWidget(self.stop_button)
        head.addWidget(button('작은 상태창',self.show_mini_panel))
        outer.addWidget(header)
        body = QHBoxLayout();body.setSpacing(0);outer.addLayout(body,1)
        sidebar = QFrame();sidebar.setObjectName("Sidebar");sidebar.setFixedWidth(180)
        nav = QVBoxLayout(sidebar);nav.setContentsMargins(12,25,12,20);nav.addWidget(label("작업 공간","Muted"))
        self.nav_buttons = {}
        for key,title in (("control","제어 화면"),("guide","손동작 안내"),("practice","연습하기"),("settings","환경설정")):
            b=button(title,lambda checked=False,k=key:self.select_page(k),"Nav");b.setCheckable(True)
            self.nav_buttons[key]=b;nav.addWidget(b)
        nav.addStretch();nav.addWidget(label("시작과 중단\n\nV · 시작\n숫자 3 · 중단\n\n손을 내려도 활성 상태는 유지합니다.","Muted"))
        body.addWidget(sidebar)
        content=QWidget();layout=QVBoxLayout(content);layout.setContentsMargins(25,22,25,20);layout.setSpacing(15)
        self.banner=label("개발 시뮬레이션 · 실제 카메라·키 입력·화면 저장 없음","Banner")
        layout.addWidget(self.banner)
        self.pages=QStackedWidget();layout.addWidget(self.pages,1);body.addWidget(content,1)
        self._page_indices={}
        self._add_page("control", self._control_page())
        guide=QWidget();g=QVBoxLayout(guide);g.addWidget(label("손동작 안내","Title"))
        for text in ("V 유지 · 제어 시작 / 숫자 3 유지 · 중단", "검지 좌우 · 뒤로 / 앞으로", "V 좌우 · 탭 이동 / V 위아래 · 페이지 이동", "양손 집기 간격 · 한 단계 확대 / 축소", "검지 원 · 새로고침 / 엄지 유지 · 북마크 창", "주먹 → 펼침 · 닫은 탭 복구 / 이미지 화면 맞춤", "양손 L 프레임 · 캡처 시작"):
            g.addWidget(label(text))
        g.addWidget(label("현재 화면은 명령 정책 시뮬레이션입니다. 실제 손 인식은 아직 연결하지 않았습니다.","Muted"));g.addStretch()
        self._add_page("guide",guide)
        for key,title,detail in (("practice","연습하기","카메라를 사용한 동작 연습과 감도 추천은 구현 예정입니다."),("settings","환경설정","인식 감도·카메라·캡처 저장 폴더 설정은 구현 예정입니다.")):
            page=QWidget();page.setAccessibleDescription(detail);p=QVBoxLayout(page);p.addWidget(label(title,"Title"));p.addWidget(label(detail,"Muted"));p.addStretch();self._add_page(key,page)
        self.select_page("control")

    def _add_page(self,key,page):
        self._page_indices[key]=self.pages.addWidget(page)

    def _control_page(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(0,0,0,0);v.setSpacing(15)
        v.addWidget(label("손동작 제어","Title"));v.addWidget(label("확정 동작 예시로 명령의 승인·보류·중단을 확인하세요.","Muted"))
        modes=QHBoxLayout();self.mode_buttons={}
        for mode,title in ((Mode.BROWSER,"브라우저 · 페이지와 탭"),(Mode.IMAGE,"이미지·발표 · 사진 넘기기")):
            b=button(title,lambda checked=False,m=mode:self.controller.set_mode(m));b.setCheckable(True);modes.addWidget(b);self.mode_buttons[mode]=b
        v.addLayout(modes)
        self.target_label=label("가상 Chrome 대상","Muted");v.addWidget(self.target_label)
        area=QHBoxLayout();area.setSpacing(16)
        preview,p=card();self.preview_label=label("카메라 미리보기\n\n카메라 연결 준비 중\n\n지금은 아래 버튼으로 명령 흐름을 시험할 수 있습니다.","Muted")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter);p.addWidget(self.preview_label,1);area.addWidget(preview,3)
        feedback,f=card();f.addWidget(label("현재 인식","Muted"));self.gesture_label=label("손동작 대기","Value");f.addWidget(self.gesture_label)
        f.addWidget(label("최근 실행","Muted"));self.command_label=label("명령 대기","Value");f.addWidget(self.command_label)
        self.detail_label=label("실제 키 입력은 보내지 않습니다.","Muted");f.addWidget(self.detail_label)
        self.reason_label=label("","Muted");f.addStretch();f.addWidget(self.reason_label);area.addWidget(feedback,2);v.addLayout(area,1)
        self.start_button=button("V 시작 예시",lambda:self._simulate(Gesture.START),"Primary")
        self.neutral_button=button("자세 해제 예시",lambda:self.controller.neutral(True))
        self.back_button=button("검지 왼쪽 쓸기",lambda:self._simulate(Gesture.LEFT))
        row=QHBoxLayout();row.addWidget(self.start_button);row.addWidget(self.neutral_button);row.addWidget(self.back_button)
        row.addWidget(button("대상 창 변경 예시",self._toggle_target));v.addLayout(row)
        extra=QHBoxLayout();self.gesture_combo=QComboBox()
        for gesture in Gesture:self.gesture_combo.addItem(f"{gesture.value} · {gesture.name}",gesture)
        extra.addWidget(self.gesture_combo);extra.addWidget(button("선택한 동작 예시",lambda:self._simulate(self.gesture_combo.currentData())));extra.addWidget(button("계속",self.controller.ack_confirmation));v.addLayout(extra)
        if self.controller.state.execution_mode!=ExecutionMode.SIMULATED:
            for layout in (row,extra):
                for i in range(layout.count()):
                    layout.itemAt(i).widget().setVisible(False)
            self.preview_label.setText('카메라 미리보기\n\n카메라 연결 준비 중\n손 인식 기능은 아직 연결하지 않았습니다.')
            self.detail_label.setText('실행 결과는 OS 전송 여부입니다. 페이지 동작은 별도로 확인하세요.')
        return page

    def select_page(self,key):
        self.pages.setCurrentIndex(self._page_indices[key])
        for name,b in self.nav_buttons.items():b.setChecked(name==key)
        if key=="practice":self.controller.stop("연습 화면")

    def _simulate(self,gesture):
        if self.controller.state.execution_mode!=ExecutionMode.SIMULATED:
            return
        now=self.runtime.clock.now_ms()
        self.controller.show_candidate(f"동작 예시 · {gesture.value}",( "simulated-hand",))
        self.controller.handle(GestureEvent(self.runtime.ids.next_id("event"),gesture,("simulated-hand",),now,now,self.controller.state.context_version,self.controller.state.camera_epoch))
        self.controller.flush_executor()

    def _toggle_target(self):
        fg=self.runtime.foreground
        if fg.snapshot().is_chrome:fg.set_other()
        else:fg.set_chrome()
        self.controller.refresh_target()
        self.render_state(self.controller.state)

    def _tick(self):
        self.runtime.pump()
        self.runtime.scheduler.run_due()
        self.controller.tick()
        self._render_target()

    def _render_target(self):
        simulated=self.controller.state.execution_mode==ExecutionMode.SIMULATED
        prefix='가상 대상: ' if simulated else '현재 전경: '
        self.target_label.setText(prefix+('Chrome' if self.runtime.foreground.snapshot().is_chrome else '다른 앱 · Chrome를 선택하세요'))

    def show_mini_panel(self):
        screen=self.screen().availableGeometry()
        self.mini_panel.move(screen.right()-350,screen.top()+35)
        self.mini_panel.show()

    def open_main(self):
        # Only this explicit user action is allowed to activate HAND's main window.
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def nativeEvent(self,event_type,message):
        if getattr(self,'hotkey',None):
            from ctypes import wintypes
            msg=wintypes.MSG.from_address(int(message))
            if self.hotkey.dispatch(msg.message,msg.wParam):
                return True,0
        return super().nativeEvent(event_type,message)

    def render_state(self,state):
        active=state.activation==Activation.ACTIVE
        self.state_label.setText("제어 중" if active and state.ready else "제어 중 · 새 동작 대기" if active else "제어 대기")
        self.gesture_label.setText(state.last_candidate)
        for mode,b in self.mode_buttons.items():b.setChecked(mode==state.mode)
        self._render_target()
        self.mini_panel.render_state(state)
        if state.last_execution:
            result=state.last_execution
            titles={Status.SENT:"가상 전송 기록",Status.APPLIED:"앱 내부 적용",Status.BLOCKED:"실행 보류",Status.FAILED:"입력 실패",Status.CANCELLED:"취소"}
            if state.execution_mode==ExecutionMode.REAL:titles[Status.SENT]='OS 키 전송 완료'
            self.command_label.setText(titles[result.status])
            reasons={"SIMULATED":"실제 키 입력을 보내지 않은 시뮬레이션입니다.","WAITING":"V로 먼저 시작하세요.","REARM_REQUIRED":"자세를 풀고 잠시 기다리세요.","TARGET_NOT_CHROME":"Chrome 창을 선택하세요.","TARGET_CHANGED":"대상 창이 바뀌어 전송하지 않았습니다.","NOT_IMPLEMENTED":"이 기능은 아직 구현 중입니다.","INPUT_BLOCKED":"입력 보류 중입니다. 상태를 확인하세요.","DUPLICATE":"같은 동작을 중복 실행하지 않았습니다."}
            reasons.update({'OS_INPUT_SENT':'OS에 키 입력을 전송했습니다. 페이지 동작까지 확인한 결과는 아닙니다.',
                            'KEYBOARD_BUSY':'누르고 있는 키를 놓고 새 동작을 해주세요.',
                            'SENDINPUT_PARTIAL':'키 전송에 실패해 제어를 중단했습니다. 입력 권한 또는 환경을 확인하세요.'})
            self.detail_label.setText(reasons.get(result.reason,result.reason))
        self.reason_label.setText(f"최근 중단: {state.last_stop_reason}" if state.last_stop_reason else "")

    def closeEvent(self,event):
        self.timer.stop()
        self.controller.stop("앱 종료")
        if self.hotkey:self.shutdown_ok=self.hotkey.close()
        self.mini_panel.close()
        self.shutdown_ok=self.runtime.close() and self.shutdown_ok
        self.runtime.ui.listener=None
        event.accept()
