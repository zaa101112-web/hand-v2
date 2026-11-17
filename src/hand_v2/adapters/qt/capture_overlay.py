from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter,QPen,QColor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel


class CaptureOverlay(QWidget):
    def __init__(self,session,save,cancel,stop=None):
        super().__init__(None,Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.session=session;self.save=save;self.cancel=cancel;self.stop=stop or cancel;self.anchor=None
        self.setWindowTitle('HAND — 캡처 영역 선택')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.resize(round(session.display.width/session.display.scale),round(session.display.height/session.display.scale))
        layout=QVBoxLayout(self);layout.addStretch();row=QHBoxLayout();layout.addLayout(row)
        self.info=QLabel();self.info.setWordWrap(True);self.info.setStyleSheet('background:#fff;color:#172b3a;padding:12px;');row.addWidget(self.info,1)
        full=QPushButton('전체 화면');full.clicked.connect(self.fullscreen);row.addWidget(full)
        self.save_button=QPushButton('현재 화면 저장 · Enter');self.save_button.clicked.connect(save);row.addWidget(self.save_button)
        b=QPushButton('취소 · Esc');b.clicked.connect(cancel);row.addWidget(b)
        self.refresh()

    def fullscreen(self):self.session.fullscreen();self.refresh()

    def refresh(self):
        s=self.session;r=s.rect
        self.info.setText(f'{r.width} × {r.height} px · 드래그/방향키 이동 · Shift 10px · Ctrl 크기 조절\n'+
                          (s.error+' · 다시 저장하면 현재 화면을 새로 읽습니다.' if s.error else '최소 32 × 32px · 확인하기 전에는 저장하지 않습니다.'))
        self.save_button.setEnabled(r.valid and s.phase!='SAVING' and not s.worker_running and not s.closed)
        self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor(10,25,35,100));r=self.session.rect;s=self.session.display.scale
        rect=QRectF(r.left/s,r.top/s,r.width/s,r.height/s)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear);p.fillRect(rect,Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver);p.setPen(QPen(QColor('#20c9ae'),3));p.drawRect(rect);p.end()

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.session.phase!='SAVING':self.anchor=event.position()

    def mouseMoveEvent(self,event):
        if self.anchor is None:return
        a,b=self.anchor,event.position()
        self.session.select(self.session.display.physical(min(a.x(),b.x()),min(a.y(),b.y()),max(a.x(),b.x()),max(a.y(),b.y())))
        self.refresh()

    def mouseReleaseEvent(self,event):self.mouseMoveEvent(event);self.anchor=None

    def keyPressEvent(self,event):
        key=event.key();mod=event.modifiers()
        if key in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            if self.save_button.isEnabled():self.save()
        elif key==Qt.Key.Key_Escape:self.stop()
        elif key in (Qt.Key.Key_Left,Qt.Key.Key_Right,Qt.Key.Key_Up,Qt.Key.Key_Down):
            step=10 if mod & Qt.KeyboardModifier.ShiftModifier else 1
            dx=step*((key==Qt.Key.Key_Right)-(key==Qt.Key.Key_Left));dy=step*((key==Qt.Key.Key_Down)-(key==Qt.Key.Key_Up))
            self.session.adjust(dx,dy,bool(mod & Qt.KeyboardModifier.ControlModifier));self.refresh()
        else:super().keyPressEvent(event)

    def closeEvent(self,event):
        if not self.session.closed:self.cancel()
        event.accept()
