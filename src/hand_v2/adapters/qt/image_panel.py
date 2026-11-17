from PySide6.QtCore import Qt, QVariantAnimation, QRectF, QEasingCurve
from PySide6.QtGui import QPainter, QImage, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from hand_v2.domain.models import Action


class ImageCanvas(QWidget):
    def __init__(self, gallery, parent=None):
        super().__init__(parent);self.gallery=gallery;self.setMinimumHeight(230)
        self.offset=0.;self.revision=-1;self.image=None;self.key=None
        self.animation=QVariantAnimation(self);self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._offset)

    def _offset(self,value):self.offset=float(value);self.update()

    def refresh(self):
        g=self.gallery
        if self.revision==g.revision:return
        changed=self.key!=(g.current.key if g.current else None)
        self.revision=g.revision
        if g.current and changed:
            a=g.current;self.key=a.key
            self.image=QImage(a.rgba,a.width,a.height,a.width*4,QImage.Format.Format_RGBA8888).copy()
        self.animation.stop();self.offset=0
        if changed and g.direction:
            self.animation.setStartValue(float(g.direction*self.width()));self.animation.setEndValue(0.);self.animation.start()
        self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#e7edf2'))
        if self.image and not self.image.isNull():
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            factor=min(self.width()/self.image.width(),self.height()/self.image.height())*self.gallery.scale
            w,h=self.image.width()*factor,self.image.height()*factor
            p.drawImage(QRectF((self.width()-w)/2+self.offset,(self.height()-h)/2,w,h),self.image)
        else:p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,'이미지 파일 또는 폴더를 여세요.')
        p.end()


class ImagePanel(QWidget):
    def __init__(self, workspace, open_files, parent=None):
        super().__init__(parent);self.workspace=workspace;self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout=QVBoxLayout(self);row=QHBoxLayout();layout.addLayout(row)
        for title,callback in [('파일 열기',lambda:open_files(False)),('폴더 열기',lambda:open_files(True))]:
            b=QPushButton(title);b.clicked.connect(callback);row.addWidget(b)
        self.previous_button=self._button('← 이전',Action.PREV_IMAGE,row)
        self.next_button=self._button('다음 →',Action.NEXT_IMAGE,row)
        self._button('−',Action.ZOOM_OUT,row);self._button('+',Action.ZOOM_IN,row);self._button('화면 맞춤 · 0',Action.FIT_IMAGE,row)
        self.canvas=ImageCanvas(workspace.gallery);layout.addWidget(self.canvas,1)
        self.info=QLabel();self.info.setWordWrap(True);layout.addWidget(self.info)
        self.excluded=QLabel();self.excluded.setWordWrap(True);layout.addWidget(self.excluded)

    def _button(self,title,action,row):
        b=QPushButton(title);b.clicked.connect(lambda:self.apply(action));row.addWidget(b);return b

    def apply(self,action):self.workspace.image_action(action);self.refresh()

    def refresh(self):
        g=self.workspace.gallery;self.canvas.refresh()
        self.info.setText(f'{g.index+1} / {len(g.assets)} · 화면 맞춤 대비 {g.scale:.0%} · {g.current.key}' if g.current else 'PNG / JPG / JPEG · ← → 이동, + − 확대·축소, 0 화면 맞춤')
        self.previous_button.setEnabled(bool(g.current) and g.index>0)
        self.next_button.setEnabled(bool(g.current) and g.index<len(g.assets)-1)

    def keyPressEvent(self,event):
        mapping={Qt.Key.Key_Left:Action.PREV_IMAGE,Qt.Key.Key_Right:Action.NEXT_IMAGE,
                 Qt.Key.Key_Plus:Action.ZOOM_IN,Qt.Key.Key_Equal:Action.ZOOM_IN,
                 Qt.Key.Key_Minus:Action.ZOOM_OUT,Qt.Key.Key_0:Action.FIT_IMAGE}
        if event.key() in mapping:self.apply(mapping[event.key()]);event.accept()
        else:super().keyPressEvent(event)
