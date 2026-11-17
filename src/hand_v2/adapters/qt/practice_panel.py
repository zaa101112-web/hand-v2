from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox
from hand_v2.domain.models import Gesture,GestureEvent
from hand_v2.application.practice import PracticeProgress


class PracticePanel(QWidget):
    def __init__(self,runtime,camera_toggle):
        super().__init__();self.runtime=runtime;self.demo=False
        self.setAccessibleDescription('카메라를 사용한 안전한 손동작 연습. 실제 키와 캡처 저장 없음.')
        v=QVBoxLayout(self);title=QLabel('연습하기');title.setObjectName('Title');v.addWidget(title)
        self.status=QLabel('실제 키 입력·파일 저장 없이 연습합니다.');self.status.setWordWrap(True);v.addWidget(self.status)
        self.preview=QLabel('카메라를 켜면 손 관절과 인식 문구를 확인할 수 있습니다.');self.preview.setMinimumSize(320,240);v.addWidget(self.preview)
        row=QHBoxLayout();v.addLayout(row)
        b=QPushButton('카메라 켜기 / 끄기');b.clicked.connect(camera_toggle);row.addWidget(b)
        stop=QPushButton('연습 중단');stop.clicked.connect(lambda:runtime.stop('연습 중단'));row.addWidget(stop)
        self.tasks=QLabel();self.tasks.setWordWrap(True);v.addWidget(self.tasks)
        self.feedback=QLabel();self.feedback.setWordWrap(True);v.addWidget(self.feedback)
        explanation=QLabel('V 0.6초 → 손 펼침 → 검지 좌우 쓸기 → 손 펼침 → 양손 집기 확대 → 숫자 3 0.35초.\n카메라가 없으면 아래 예시로 화면 흐름만 확인할 수 있습니다. 예시는 손 인식 검증으로 세지 않습니다.')
        explanation.setWordWrap(True);v.addWidget(explanation)
        demo_row=QHBoxLayout();v.addLayout(demo_row);self.gestures=QComboBox()
        for g in Gesture:self.gestures.addItem(g.value+' '+g.name,g)
        demo_row.addWidget(self.gestures)
        demo=QPushButton('가상 동작 예시 실행');demo.clicked.connect(self.example);demo_row.addWidget(demo)
        neutral=QPushButton('가상 자세 해제');neutral.clicked.connect(self.neutral);demo_row.addWidget(neutral)
        v.addStretch();self.layout_box=v

    def example(self):
        p=self.runtime.practice_runtime
        if not p:return
        self.demo=True;p.controller.camera_connected(p.controller.state.camera_epoch)
        now=p.clock.now_ms();g=self.gestures.currentData();s=p.controller.state
        p.controller.handle(GestureEvent(p.ids.next_id('demo'),g,('demo-hand',),now,now,s.context_version,s.camera_epoch))
        p.controller.flush_executor();self.refresh()

    def neutral(self):
        p=self.runtime.practice_runtime
        if p:self.demo=True;p.controller.neutral(True)

    def refresh(self):
        p=self.runtime.practice_runtime
        if not p:self.status.setText('입력 해제 확인 후 연습을 시작합니다. 실제 키 입력·저장 없음.');return
        s=p.controller.state;r=p.vision.last_recognition
        self.status.setText(('가상 예시 포함 · ' if self.demo else '실제 카메라 연습 · ')+
                            '실제 키 입력·파일 저장 없음 · '+('카메라 연결됨' if self.runtime.controller.state.camera_status=='CONNECTED' else '카메라를 켜주세요'))
        self.feedback.setText(f'{s.activation.value} · {s.last_candidate}\n'+('가상 결과: '+s.last_execution.reason if s.last_execution else '명령 대기'))
        progress=self.runtime.practice_progress
        self.tasks.setText('\n'.join(('✓ ' if gesture in progress.completed else '○ ')+name for name,gesture in PracticeProgress.TASKS))
