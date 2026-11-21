from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox
from hand_v2.domain.models import Gesture,GestureEvent
from hand_v2.application.practice import PracticeProgress


class PracticePanel(QWidget):
    def __init__(self,runtime,camera_toggle,after_release):
        super().__init__();self.runtime=runtime;self.demo=False;self.after_release=after_release;self.applied=False
        self.setAccessibleDescription('카메라를 사용한 안전한 손동작 연습. 실제 키와 캡처 저장 없음.')
        v=QVBoxLayout(self);title=QLabel('연습하기');title.setObjectName('Title');v.addWidget(title)
        self.status=QLabel('실제 키 입력·파일 저장 없이 연습합니다.');self.status.setWordWrap(True);v.addWidget(self.status)
        self.preview=QLabel('카메라를 켜면 손 관절과 인식 문구를 확인할 수 있습니다.');self.preview.setMinimumSize(320,240);v.addWidget(self.preview)
        row=QHBoxLayout();v.addLayout(row)
        b=QPushButton('카메라 켜기 / 끄기');b.clicked.connect(camera_toggle);row.addWidget(b)
        stop=QPushButton('연습 중단');stop.clicked.connect(lambda:runtime.stop('연습 중단'));row.addWidget(stop)
        self.tasks=QLabel();self.tasks.setWordWrap(True);v.addWidget(self.tasks)
        self.feedback=QLabel();self.feedback.setWordWrap(True);v.addWidget(self.feedback)
        explanation=QLabel('V 0.6초 → 잠깐 멈춤 → 검지 좌우 쓸기. 동작 끝에서 잠깐 멈추면 손을 펼치지 않고 다음 동작을 할 수 있습니다. 양손 엄지·검지를 집은 채 간격을 계속 바꾸면 연속 확대·축소합니다.\n카메라가 없으면 아래 예시로 화면 흐름만 확인할 수 있습니다. 예시는 손 인식 검증으로 세지 않습니다.')
        explanation.setWordWrap(True);v.addWidget(explanation)
        self.assessment_info=QLabel('연속 동작 측정 · 카메라를 켠 뒤 시작하세요.');self.assessment_info.setWordWrap(True);v.addWidget(self.assessment_info)
        assessment_row=QHBoxLayout();v.addLayout(assessment_row)
        self.assessment_start=QPushButton('연속 동작 8과제 측정');self.assessment_start.clicked.connect(self.start_assessment);assessment_row.addWidget(self.assessment_start)
        self.assessment_copy=QPushButton('결과 JSON 복사');self.assessment_copy.clicked.connect(self.copy_assessment);assessment_row.addWidget(self.assessment_copy)
        self.assessment_copy.setEnabled(False)
        demo_row=QHBoxLayout();v.addLayout(demo_row);self.gestures=QComboBox()
        for g in Gesture:self.gestures.addItem(g.value+' '+g.name,g)
        demo_row.addWidget(self.gestures)
        demo=QPushButton('가상 동작 예시 실행');demo.clicked.connect(self.example);demo_row.addWidget(demo)
        neutral=QPushButton('가상 자세 해제');neutral.clicked.connect(self.neutral);demo_row.addWidget(neutral)
        self.calibration_info=QLabel();self.calibration_info.setWordWrap(True);v.addWidget(self.calibration_info)
        calibration_row=QHBoxLayout();v.addLayout(calibration_row)
        start=QPushButton('감도 추천 측정 시작');start.clicked.connect(self.start_calibration);calibration_row.addWidget(start)
        cancel=QPushButton('측정 취소');cancel.clicked.connect(lambda:runtime.calibration.cancel() if runtime.calibration else None);calibration_row.addWidget(cancel)
        self.apply_recommendation=QPushButton('추천값 저장 및 적용');self.apply_recommendation.clicked.connect(self.apply_calibration);calibration_row.addWidget(self.apply_recommendation)
        self.apply_recommendation.setEnabled(False)
        self.calibration_message=QLabel();self.calibration_message.setWordWrap(True);v.addWidget(self.calibration_message)
        v.addStretch();self.layout_box=v

    def start_calibration(self):
        if self.runtime.practice_assessment:self.runtime.practice_assessment.invalidate('CALIBRATION_STARTED')
        if self.runtime.calibration:
            self.runtime.calibration.start();self.applied=False;self.calibration_message.setText('카메라 앞에서 검지만 펴고 5초 동안 정지하세요. 이후 매번 손을 펼친 뒤 좌우 각각 10회 쓸어주세요.')

    def apply_calibration(self):
        c=self.runtime.calibration
        if not c or c.phase!='READY' or c.recommendation is None:return
        patch={'gestures':{'swipe_distance':c.recommendation}}
        def apply():
            try:
                from hand_v2.domain.configuration import merge_leaves,validate_config
                value=self.runtime.config_store.save(patch) if self.runtime.config_store else validate_config(merge_leaves(self.runtime.settings,patch))
                self.runtime.apply_settings(value);self.applied=True
                self.calibration_message.setText('추천값을 적용했습니다. 손을 펼쳐 다시 준비하세요.')
            except (ValueError,OSError) as exc:self.calibration_message.setText('추천값을 적용하지 않았습니다: '+str(exc))
        self.after_release(apply)

    def example(self):
        p=self.runtime.practice_runtime
        if not p:return
        if self.runtime.practice_assessment:self.runtime.practice_assessment.invalidate('DEMO_INPUT')
        self.demo=True;p.controller.camera_connected(p.controller.state.camera_epoch)
        now=p.clock.now_ms();g=Gesture(self.gestures.currentData());s=p.controller.state
        p.controller.handle(GestureEvent(p.ids.next_id('demo'),g,('demo-hand',),now,now,s.context_version,s.camera_epoch))
        p.controller.flush_executor();self.refresh()

    def neutral(self):
        p=self.runtime.practice_runtime
        if self.runtime.practice_assessment:self.runtime.practice_assessment.invalidate('DEMO_INPUT')
        if p:self.demo=True;p.controller.neutral(True)

    def start_assessment(self):
        r=self.runtime;p=r.practice_runtime;a=r.practice_assessment
        if not p or not a:return
        if r.controller.state.camera_status!='CONNECTED':
            self.assessment_info.setText('먼저 카메라를 켜주세요.');return
        if r.calibration:r.calibration.cancel()
        p.controller.stop('연속 과제 시작');p.vision.recognizer.reset()
        self.demo=False;a.start(r.clock.now_ms());self.refresh()

    def copy_assessment(self):
        from PySide6.QtWidgets import QApplication
        import json
        a=self.runtime.practice_assessment
        if not a or a.active or a.started is None:return
        report=a.report();report['settings']=self.runtime.settings
        QApplication.clipboard().setText(json.dumps(report,ensure_ascii=False,indent=2))

    def refresh_assessment(self):
        a=self.runtime.practice_assessment
        if not a:return
        text=a.prompt()
        report=a.report()
        if report['complete'] and report['valid']:
            text+=f"\n인식 {report['recognized']}/{report['expected']} · 가상 실행 {report['executed']}/{report['expected']} · 누락 {report['missed']} · 다른 동작 {report['wrong']} · 중복 {report['duplicates']}"
            text+='\n카메라 연습 결과입니다. 실제 Chrome 효과·3명 정확도 검증과 구분합니다.'
        self.assessment_info.setText(text)
        self.assessment_start.setEnabled(not a.active)
        self.assessment_copy.setEnabled(a.started is not None and not a.active)

    def refresh(self):
        self.refresh_assessment()
        p=self.runtime.practice_runtime
        if not p:self.status.setText('입력 해제 확인 후 연습을 시작합니다. 실제 키 입력·저장 없음.');return
        s=p.controller.state;r=p.vision.last_recognition
        self.status.setText(('가상 예시 포함 · ' if self.demo else '실제 카메라 연습 · ')+
                            '실제 키 입력·파일 저장 없음 · '+('카메라 연결됨' if self.runtime.controller.state.camera_status=='CONNECTED' else '카메라를 켜주세요'))
        self.feedback.setText(f'{s.activation.value} · {s.last_candidate}\n'+('가상 결과: '+s.last_execution.reason if s.last_execution else '명령 대기'))
        progress=self.runtime.practice_progress
        self.tasks.setText('\n'.join(('✓ ' if gesture in progress.completed else '○ ')+name for name,gesture in PracticeProgress.TASKS))
        c=self.runtime.calibration
        if c:
            phases={'IDLE':'측정 전','STILL':'검지를 편 채 5초 정지','LEFT':'손 펼침 → 검지 왼쪽 쓸기','RIGHT':'손 펼침 → 검지 오른쪽 쓸기','READY':'추천 준비 완료','ERROR':'추천 보류'}
            self.calibration_info.setText(f"감도 추천 · {phases.get(c.phase,c.phase)}\n정지 {min(c.still_ms,5000)/1000:.1f}/5초 · 왼쪽 {len(c.left)}/10 · 오른쪽 {len(c.right)}/10\n현재 {self.runtime.settings['gestures']['swipe_distance']:.2f}"+
                (f' → 추천 {c.recommendation:.2f} (자동 적용하지 않음)' if c.recommendation is not None else '')+('\n'+c.error if c.error else ''))
            self.apply_recommendation.setEnabled(c.phase=='READY' and not self.applied)
