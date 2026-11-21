from PySide6.QtWidgets import QWidget,QVBoxLayout,QFormLayout,QLabel,QComboBox,QCheckBox,QDoubleSpinBox,QSpinBox,QLineEdit,QPushButton,QFileDialog


class SettingsPanel(QWidget):
    def __init__(self,runtime,after_release,on_applied):
        super().__init__();self.runtime=runtime;self.after_release=after_release;self.on_applied=on_applied
        self.setAccessibleDescription('카메라, 인식 감도, 캡처 저장 폴더와 로그 수준 설정')
        v=QVBoxLayout(self);title=QLabel('환경설정');title.setObjectName('Title');v.addWidget(title)
        self.form=QFormLayout();v.addLayout(self.form)
        self.camera=QComboBox()
        for i in range(4):self.camera.addItem(f'카메라 {i}',i)
        self.form.addRow('카메라',self.camera)
        self.preview=QCheckBox('미리보기 표시');self.form.addRow('영상 표시',self.preview)
        self.swipe=self.number('쓸기 거리 · 화면 비율',.10,.25,.01)
        self.smoothing=QSpinBox();self.smoothing.setRange(30,120);self.smoothing.setSuffix(' ms');self.form.addRow('움직임 평활화',self.smoothing)
        self.pinch_enter=self.number('집기 시작 비율',.20,.35,.01)
        self.pinch_exit=self.number('집기 해제 비율',.40,.60,.01)
        self.zoom=self.number('양손 확대 확정 비율',1.10,1.30,.01)
        self.folder=QLineEdit();self.folder.setPlaceholderText('기본값: Windows 사진 폴더 / HAND-v2');self.form.addRow('캡처 저장 폴더',self.folder)
        choose=QPushButton('저장 폴더 선택');choose.clicked.connect(self.choose_folder);self.form.addRow('',choose)
        self.log=QComboBox();self.log.addItems(['DEBUG','INFO','WARNING','ERROR']);self.form.addRow('진단 로그 수준',self.log)
        policy=QLabel('시작 600ms · 중단 350ms · 동작 준비 180ms · 입력 시효 250ms는 안전 정책으로 고정됩니다.\n카메라를 변경하면 제어 대기로 돌아갑니다. 그 밖의 변경 후에는 잠깐 멈춰 다시 준비하세요.')
        policy.setWordWrap(True);v.addWidget(policy)
        self.message=QLabel();self.message.setWordWrap(True);v.addWidget(self.message)
        self.save_button=QPushButton('설정 저장 및 적용');self.save_button.clicked.connect(self.save);v.addWidget(self.save_button);v.addStretch()
        self.reload()

    def number(self,title,low,high,step):
        widget=QDoubleSpinBox();widget.setDecimals(2);widget.setRange(low,high);widget.setSingleStep(step);self.form.addRow(title,widget);return widget

    def reload(self):
        s=self.runtime.settings;g=s['gestures']
        self.camera.setCurrentIndex(s['camera']['index']);self.preview.setChecked(s['display']['preview'])
        self.swipe.setValue(g['swipe_distance']);self.smoothing.setValue(g['smoothing_tau_ms'])
        self.pinch_enter.setValue(g['pinch_enter']);self.pinch_exit.setValue(g['pinch_exit']);self.zoom.setValue(g['zoom_step_ratio'])
        self.folder.setText(s['capture']['folder'] or '');self.log.setCurrentText(s['logging']['level'])

    def choose_folder(self):
        def choose():
            path=QFileDialog.getExistingDirectory(self,'캡처 저장 폴더',self.folder.text())
            if path:self.folder.setText(path)
        self.after_release(choose)

    def save(self):
        patch={'camera':{'index':self.camera.currentData()},'display':{'preview':self.preview.isChecked()},
               'gestures':{'swipe_distance':self.swipe.value(),'smoothing_tau_ms':self.smoothing.value(),
                           'pinch_enter':self.pinch_enter.value(),'pinch_exit':self.pinch_exit.value(),'zoom_step_ratio':self.zoom.value()},
               'capture':{'folder':self.folder.text().strip() or None},'logging':{'level':self.log.currentText()}}
        def apply():
            try:
                if self.runtime.config_store:value=self.runtime.config_store.save(patch)
                else:
                    from hand_v2.domain.configuration import merge_leaves,validate_config
                    value=validate_config(merge_leaves(self.runtime.settings,patch))
                self.runtime.apply_settings(value);self.on_applied()
                self.message.setText('설정을 저장하고 적용했습니다.' if self.runtime.config_store else '가상 실행에 설정을 적용했습니다. 파일은 저장하지 않았습니다.')
            except (ValueError,OSError) as exc:self.message.setText('설정을 적용하지 않았습니다. '+str(exc))
        if not self.after_release(apply):self.message.setText('다른 작업이 끝난 뒤 다시 저장하세요.')
