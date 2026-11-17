from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut,QImage,QPixmap,QPainter,QPen,QColor
from PySide6.QtWidgets import (QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QScrollArea, QComboBox,QCheckBox,QFileDialog)

from hand_v2.domain.models import Activation, ExecutionMode, Gesture, GestureEvent, Mode, Status
from .controller_bridge import ControllerBridge
from .control_status import control_status
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
        self._closing=False
        self._close_started=None
        self._practice_requested=False
        self.setWindowTitle("HAND v2 — 손동작 단축키 제어")
        self.resize(1280,860)
        self.setMinimumSize(800,600)
        self.setStyleSheet(STYLE)
        self._build()
        self.hotkey=None
        self.shutdown_ok=True
        from .mini_panel import MiniPanel
        self.mini_panel=MiniPanel(self.controller,self.open_main)
        from .capture_ui import CaptureUi
        self.capture_ui=CaptureUi(self,runtime)
        self.capture_shortcut=QShortcut(QKeySequence('Ctrl+Shift+S'),self)
        self.capture_shortcut.activated.connect(runtime.workspace.request_capture)
        self._dialog_request=None
        if runtime.controller.state.execution_mode==ExecutionMode.REAL:
            from hand_v2.adapters.windows.hotkey import GlobalStopHotkey
            self.hotkey=GlobalStopHotkey(int(self.winId()),lambda:runtime.stop('전역 F8'),runtime.foreground.native)
            self.banner.setText('카메라를 켜고 V를 0.6초 유지해 시작하세요. '+
                                ('전역 F8 중단 사용 가능' if self.hotkey.registered else 'F8 등록 실패 · 중단 버튼/숫자 3을 사용하세요'))
        self.bridge = ControllerBridge(self)
        self.bridge.state_changed.connect(self.render_state)
        runtime.ui.listener = self.bridge.render_state
        runtime.preview_listener=self.render_preview
        self.render_state(self.controller.state)
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.escape = QShortcut(QKeySequence("Escape"),self)
        self.escape.activated.connect(lambda:runtime.stop("Esc"))
        self.camera_combo.setCurrentIndex(runtime.camera_index)
        self.preview_checkbox.setChecked(runtime.preview_enabled)

    def _build(self):
        root = QWidget(); root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        header = QFrame();header.setObjectName("Header")
        head = QHBoxLayout(header);head.setContentsMargins(25,17,25,17)
        head.addWidget(label("HAND","Logo"));head.addWidget(label("손동작 단축키 제어","Muted"));head.addStretch()
        self.state_label = label("제어 대기");head.addWidget(self.state_label)
        self.stop_button = button("중단",lambda:self.runtime.stop("중단 버튼"),"Stop");head.addWidget(self.stop_button)
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
        for text in ("V 0.6초 · 시작 / 숫자 3(엄지·검지·중지) 0.35초 · 중단", "검지 좌우 · 뒤로 / 앞으로, 이미지 모드에서는 이전 / 다음", "V 좌우 · 탭 이동 / V 위아래 · 페이지 이동", "양손 엄지·검지 집기 → 간격 벌리기/좁히기 · 한 단계 확대/축소", "검지 원 · 새로고침 / 엄지 0.6초 · 북마크 창", "주먹 0.25초 → 1.2초 이내 손 펼치기 · 닫은 탭 복구 / 이미지 화면 맞춤", "양손 L 0.8초 · 영역 캡처 시작, 실제 마우스/키보드로 영역 선택 후 Enter 저장"):
            g.addWidget(label(text))
        g.addWidget(label("각 명령 후 손을 펼쳐 자세를 해제하세요. 숫자 3, F8 또는 중단 버튼으로 중단합니다. 북마크 창을 닫은 뒤 작은 상태창에서 ‘계속’을 눌러야 다른 명령을 실행할 수 있습니다. 손을 내려도 활성 상태는 유지됩니다.","Muted"));g.addStretch()
        self._add_page("guide",guide)
        from .practice_panel import PracticePanel
        from .settings_panel import SettingsPanel
        self.practice_panel=PracticePanel(self.runtime,self.toggle_camera,self.after_release)
        self.settings_panel=SettingsPanel(self.runtime,self.after_release,self.settings_applied)
        self._add_page('practice',self.practice_panel);self._add_page('settings',self.settings_panel)
        self.select_page("control")

    def _add_page(self,key,page):
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page)
        scroll.setAccessibleDescription(page.accessibleDescription() or key)
        self._page_indices[key]=self.pages.addWidget(scroll)

    def _control_page(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(0,0,0,0);v.setSpacing(15)
        v.addWidget(label("손동작 제어","Title"));v.addWidget(label("카메라로 손동작을 인식해 단축키를 실행합니다. 시작 후 손을 펼쳐 자세를 해제하세요.","Muted"))
        modes=QHBoxLayout();self.mode_buttons={}
        for mode,title in ((Mode.BROWSER,"브라우저 · 페이지와 탭"),(Mode.IMAGE,"이미지·발표 · 사진 넘기기")):
            b=button(title,lambda checked=False,m=mode:self.controller.set_mode(m));b.setCheckable(True);modes.addWidget(b);self.mode_buttons[mode]=b
        v.addLayout(modes)
        self.target_label=label("가상 Chrome 대상","Muted");v.addWidget(self.target_label)
        from .image_panel import ImagePanel
        self.image_panel=ImagePanel(self.runtime.workspace,self.open_images)
        v.addWidget(self.image_panel,1);self.image_panel.hide()
        capture_row=QHBoxLayout();capture_row.addWidget(button('영역 캡처 · Ctrl+Shift+S',self.runtime.workspace.request_capture))
        self.capture_notice=label('확인 버튼 또는 Enter를 눌렀을 때 현재 화면을 저장합니다.','Muted')
        capture_row.addWidget(self.capture_notice,1);v.addLayout(capture_row)
        area=QHBoxLayout();area.setSpacing(16)
        preview,p=card();self.preview_label=label("카메라 미리보기\n\n카메라를 켜면 손의 관절과 인식 결과가 표시됩니다.","Muted")
        self.preview_label.setMinimumSize(360,270)
        controls=QHBoxLayout()
        self.camera_combo=QComboBox()
        for index in range(4):self.camera_combo.addItem(f'카메라 {index}',index)
        self.camera_button=button('카메라 켜기',self.toggle_camera,'Primary')
        self.preview_checkbox=QCheckBox('미리보기');self.preview_checkbox.setChecked(True)
        self.preview_checkbox.toggled.connect(self.toggle_preview)
        controls.addWidget(self.camera_combo);controls.addWidget(self.camera_button);controls.addWidget(self.preview_checkbox);p.addLayout(controls)
        self.camera_info=label('카메라 꺼짐','Muted');p.addWidget(self.camera_info)
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
            self.preview_label.setText('카메라를 켜고 손을 보여주세요.\nV 0.6초: 시작 · 숫자 3 0.35초: 중단\n검지 좌우: 뒤로/앞으로 · V 좌우: 탭 · V 위아래: 페이지')
            self.detail_label.setText('실행 결과는 OS 전송 여부입니다. 페이지 동작은 별도로 확인하세요.')
        return page

    def select_page(self,key):
        if key!='practice' and (self._practice_requested or self.runtime.practice_runtime):
            self._practice_requested=False;self.runtime.exit_practice()
        self.pages.setCurrentIndex(self._page_indices[key])
        for name,b in self.nav_buttons.items():b.setChecked(name==key)
        if key=="practice":
            self.runtime.stop('연습 화면');self._practice_requested=True
        if key=='settings' and hasattr(self,'_dialog_request'):
            self.after_release(self.settings_panel.reload)

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
        if self._practice_requested:self.runtime.enter_practice()
        self.practice_panel.refresh()
        self.capture_ui.tick()
        self._poll_dialog()
        for result,error in self.runtime.image_loader.poll():
            if result:
                self.runtime.workspace.gallery.replace(result.assets)
                self.image_panel.excluded.setText('제외한 파일:\n'+'\n'.join(result.excluded) if result.excluded else '')
                if not result.assets:self.image_panel.excluded.setText('열 수 있는 이미지가 없어 기존 목록을 유지했습니다.\n'+'\n'.join(result.excluded))
            else:self.image_panel.excluded.setText('이미지를 열지 못했습니다: '+error)
        self.image_panel.refresh()
        self.image_panel.setVisible(self.controller.state.mode==Mode.IMAGE)
        self._render_target()
        if getattr(self.runtime.events,'error',''):
            self.capture_notice.setText('진단 로그 저장을 확인하세요. 제어 상태는 별도로 유지됩니다. '+self.runtime.events.error)
        camera=self.runtime.camera
        running=bool(camera and camera.session is not None)
        self.camera_button.setText('카메라 끄기' if self.runtime.camera_wanted else '카메라 켜기')
        self.camera_combo.setEnabled(not running)
        state=self.controller.state.camera_status
        self.camera_info.setText(f'카메라 연결됨 · {self.runtime.camera_fps:.1f} fps' if state=='CONNECTED' else
                                 '카메라 연결 중…' if state=='CONNECTING' else '카메라 꺼짐 / 연결 확인 필요')
        if self._closing:
            elapsed=self.runtime.clock.now_ms()-self._close_started
            capture=self.runtime.capture_worker
            if capture and capture.busy and elapsed>=5000:
                self.shutdown_ok=False;capture.abort()
            busy=running or bool(capture and capture.busy) or self.runtime.image_loader.busy
            if not busy:self.close()
            elif (running and elapsed>=4500) or elapsed>=10000:
                self.shutdown_ok=False
                from PySide6.QtWidgets import QApplication
                QApplication.instance().exit(2)

    def toggle_camera(self):
        if self.runtime.camera_wanted:
            self.runtime.stop_camera();self.preview_label.clear();self.preview_label.setText('카메라를 껐습니다.')
        else:
            if not self.runtime.start_camera(self.camera_combo.currentData(),self.preview_checkbox.isChecked()):
                self.preview_label.setText('카메라를 시작하지 못했습니다. 다른 카메라를 선택하세요.')
        self._tick()

    def after_release(self,callback):
        if self._dialog_request or self.controller.state.dialog_lock or self.controller.state.mode==Mode.CAPTURE:return False
        self.controller.set_dialog_lock(True)
        self._dialog_request=(callback,self.controller.state.context_version,self.runtime.clock.now_ms()+1000)
        return True

    def _poll_dialog(self):
        if not self._dialog_request:return
        callback,context,deadline=self._dialog_request
        if context!=self.controller.state.context_version or self.runtime.clock.now_ms()>deadline:
            self._dialog_request=None;self.controller.set_dialog_lock(False)
            self.capture_notice.setText('입력 해제 확인이 완료되지 않아 요청을 취소했습니다.');return
        if self.controller.state.release_pending:return
        self._dialog_request=None
        try:callback()
        finally:self.controller.set_dialog_lock(False)

    def open_images(self,folder=False):
        def select():
            if folder:
                path=QFileDialog.getExistingDirectory(self,'이미지 폴더 선택');paths=[path] if path else []
            else:paths,_=QFileDialog.getOpenFileNames(self,'이미지 파일 선택','','이미지 (*.png *.jpg *.jpeg *.PNG *.JPG *.JPEG)')
            if paths:
                self.runtime.image_loader.submit(paths);self.image_panel.excluded.setText('이미지를 읽는 중입니다…')
        self.after_release(select)

    def settings_applied(self):
        self.camera_combo.setCurrentIndex(self.runtime.camera_index)
        self.preview_checkbox.setChecked(self.runtime.preview_enabled)

    def toggle_preview(self,enabled):
        self.runtime.set_preview(enabled)
        if not enabled:self.preview_label.clear();self.preview_label.setText('미리보기 꺼짐 · 손동작 인식은 계속됩니다.')

    def render_preview(self,packet):
        if not self.preview_checkbox.isChecked() or self._closing:return
        frame=packet.frame
        image=QImage(packet.preview_rgb,frame.image_width,frame.image_height,frame.image_width*3,QImage.Format.Format_RGB888).copy().mirrored(True,False)
        painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#20e0b2'),2))
        chains=((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17))
        for hand in frame.hands:
            points=[(int((1-p.x)*frame.image_width),int(p.y*frame.image_height)) for p in hand.landmarks]
            for chain in chains:
                for a,b in zip(chain,chain[1:]):painter.drawLine(*points[a],*points[b])
            for x,y in points:painter.drawEllipse(x-3,y-3,6,6)
        painter.end()
        self.preview_label.setPixmap(QPixmap.fromImage(image).scaled(self.preview_label.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        if self.runtime.practice_runtime:
            target=self.practice_panel.preview
            target.setPixmap(QPixmap.fromImage(image).scaled(target.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))

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
        self.state_label.setText(control_status(state))
        self.gesture_label.setText(state.last_candidate)
        for mode,b in self.mode_buttons.items():b.setChecked(mode==state.mode)
        self._render_target()
        self.mini_panel.render_state(state)
        if state.last_execution:
            result=state.last_execution
            titles={Status.SENT:"가상 전송 기록",Status.APPLIED:"앱 내부 적용",Status.BLOCKED:"실행 보류",Status.FAILED:"입력 실패",Status.CANCELLED:"취소"}
            if state.execution_mode==ExecutionMode.REAL:titles[Status.SENT]='OS 키 전송 완료'
            self.command_label.setText(titles[result.status])
            reasons={"SIMULATED":"실제 키 입력을 보내지 않은 시뮬레이션입니다.","WAITING":"V로 먼저 시작하세요.","REARM_REQUIRED":"손을 펼쳐 ‘동작 가능’이 되면 다시 쓸어주세요.","TARGET_NOT_CHROME":"Chrome 창을 선택하세요.","TARGET_CHANGED":"대상 창이 바뀌어 전송하지 않았습니다.","NOT_IMPLEMENTED":"이 기능은 아직 구현 중입니다.","INPUT_BLOCKED":"입력 보류 중입니다. 상태를 확인하세요.","DUPLICATE":"같은 동작을 중복 실행하지 않았습니다."}
            reasons.update({'OS_INPUT_SENT':'OS에 키 입력을 전송했습니다. 페이지 동작까지 확인한 결과는 아닙니다.',
                            'KEYBOARD_BUSY':'누르고 있는 키를 놓고 새 동작을 해주세요.',
                            'SENDINPUT_PARTIAL':'키 전송에 실패해 제어를 중단했습니다. 입력 권한 또는 환경을 확인하세요.'})
            self.detail_label.setText(reasons.get(result.reason,result.reason))
        self.reason_label.setText(f"최근 중단: {state.last_stop_reason}" if state.last_stop_reason else "")

    def closeEvent(self,event):
        if not self._closing:
            self._closing=True;self._close_started=self.runtime.clock.now_ms()
            self.runtime.stop_camera()
            self.capture_ui.close()
            self.runtime.image_loader.close()
            if self.runtime.practice_runtime:self.runtime.exit_practice()
        if ((self.runtime.camera and self.runtime.camera.session is not None) or
            (self.runtime.capture_worker and self.runtime.capture_worker.busy) or self.runtime.image_loader.busy):
            self.camera_button.setEnabled(False)
            self.camera_info.setText('카메라·캡처·이미지 작업과 입력을 정리하고 있습니다…')
            event.ignore();return
        self.timer.stop()
        self.controller.stop("앱 종료")
        if self.hotkey:self.shutdown_ok=self.hotkey.close() and self.shutdown_ok
        self.mini_panel.close()
        self.shutdown_ok=self.runtime.close() and self.shutdown_ok
        self.runtime.ui.listener=None
        self.runtime.preview_listener=None
        event.accept()
