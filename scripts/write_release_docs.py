"""Render the current implementation/acceptance audit without rewriting historical evidence."""
from pathlib import Path
import json,re,html
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'docs/validation/m08-final.json').read_text(encoding='utf-8'))
STYLE='''body{font:16px/1.7 "Segoe UI","Malgun Gothic",sans-serif;color:#183442;background:#f4f7fa;margin:0}main{max-width:1100px;margin:36px auto;padding:36px;background:white;border-radius:18px}h1{font-size:36px;line-height:1.3}h2{margin-top:36px;color:#087f76}a{color:#087f76}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #dce5ec;text-align:left;padding:12px;vertical-align:top}th{background:#e8f4f1}.note{padding:18px;background:#fff6df;border-radius:10px}code{background:#edf2f5;padding:2px 5px}nav{display:flex;gap:20px;flex-wrap:wrap}@media(max-width:700px){main{margin:0;padding:20px}table{font-size:12px}th,td{padding:7px}}'''
def document(title,body):return f'<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{STYLE}</style><main>{body}</main></html>'.replace('__AUTOMATED_TESTS__',str(report['automatic']['passed']))
guide='''<nav><a href="../README.html">프로젝트 안내</a><a href="release-review.html">검증 결과</a></nav>
<h1>HAND v2 사용 안내</h1><p>손동작으로 Chrome 단축키를 실행하고, 이미지를 넘기거나 화면의 선택 영역을 저장하는 Windows 앱입니다.</p>
<h2>1. 시작과 중단</h2><ol><li><a href="../start_hand.bat">HAND 실행</a>. 실행 파일과 <code>_internal</code> 폴더를 함께 보관하세요.</li>
<li>카메라를 선택하고 <b>카메라 켜기</b>를 누릅니다. 개발에 사용한 이 PC에서는 카메라 1이 확인되었습니다.</li>
<li>손 전체가 영상 중앙에 보이게 하고 <b>V를 0.6초</b> 유지합니다. 시작 후 손을 펼쳐 <b>동작 가능</b> 표시를 확인합니다.</li>
<li>매 동작 후 손을 펼쳐 다시 준비합니다. 잠깐 자세를 잡은 다음 쓸어도 됩니다. 손을 내렸다는 이유만으로 제어가 꺼지지는 않습니다.</li>
<li><b>숫자 3(엄지·검지·중지)을 0.35초</b> 유지하거나, <b>중단 버튼 / F8</b>으로 중단합니다. F8 등록 실패는 화면 상단에 표시됩니다. Esc는 HAND 창 안에서 중단합니다.</li></ol>
<h2>2. Chrome 조작</h2><p>Chrome 창을 앞에 두세요. 뒤로/앞으로는 방문 기록이 있는 탭에서 작동합니다. 주소창이나 메뉴에 포커스가 있으면 본문을 한 번 클릭한 뒤 사용하세요. HAND의 작은 상태창으로 인식·실행·재무장 상태를 볼 수 있습니다.</p>
<table><tr><th>손동작</th><th>기능</th></tr><tr><td>검지만 펴서 왼쪽 / 오른쪽으로 쓸기</td><td>뒤로 / 앞으로</td></tr>
<tr><td>V를 왼쪽 / 오른쪽으로 쓸기</td><td>이전 / 다음 탭</td></tr><tr><td>V를 위 / 아래로 쓸기</td><td>페이지 위 / 아래</td></tr>
<tr><td>양손 엄지·검지를 집고 간격 벌리기 / 좁히기</td><td>한 단계 확대 / 축소</td></tr><tr><td>검지로 원 그리기</td><td>새로고침</td></tr>
<tr><td>엄지만 펴서 0.6초 유지</td><td>북마크 창 열기. 창을 닫은 뒤 작은 상태창의 <b>계속</b>을 누르고 손을 펼쳐 재무장합니다.</td></tr>
<tr><td>주먹 0.25초 → 1.2초 이내 손 펼치기</td><td>닫은 탭 복구</td></tr><tr><td>양손 L 모양을 서로 마주 보게 0.8초 유지</td><td>영역 캡처 시작</td></tr></table>
<p>‘OS 키 전송 완료’는 키를 보냈다는 뜻입니다. 페이지가 실제로 바뀌었는지는 별도로 확인하세요. 물리 키를 누르고 있거나 다른 앱이 앞에 있으면 입력을 보류합니다.</p>
<h2>3. 이미지·발표</h2><p>제어 화면에서 <b>이미지·발표</b>를 선택하고 파일 또는 폴더를 엽니다. PNG/JPG/JPEG, 방향 정보와 투명을 지원합니다. 파일 이름의 숫자 순서로 정렬하며 손상 파일은 제외 목록에 표시합니다. 취소하거나 유효한 파일이 없으면 기존 목록을 유지합니다.</p>
<p>검지 좌우 쓸기 또는 <b>← / →</b>로 이전·다음 이미지, 양손 집기 또는 <b>+ / −</b>로 확대·축소, 주먹→펼침 또는 <b>0</b>으로 화면 맞춤을 실행합니다. 이미지별 배율은 유지되고 첫/마지막에서 멈춥니다. 앱 버튼도 같은 기능을 사용합니다.</p>
<h2>4. 영역 캡처</h2><ol><li>양손 L, <b>영역 캡처</b> 버튼 또는 HAND 안에서 <b>Ctrl+Shift+S</b>를 사용합니다. 버튼과 키보드는 제어 대기 중에도 사용할 수 있습니다.</li>
<li>실제 마우스로 드래그하거나 방향키로 영역을 고릅니다. 방향키 1px, Shift 10px, Ctrl은 오른쪽/아래 끝점 크기 조절입니다. 전체 화면 버튼도 사용할 수 있습니다.</li>
<li><b>확인 / Enter</b>를 누르면 그 시점의 화면을 PNG로 저장합니다. 최소 크기는 실제 32×32px입니다. 저장 순간 HAND 창들은 숨겨집니다.</li>
<li>기본 저장 위치는 Windows <b>사진 / HAND-v2</b>입니다. 환경설정에서 바꿀 수 있습니다. 성공 후 실제 파일 경로를 표시합니다.</li></ol>
<p>취소 버튼은 이전 모드로 돌아갑니다. Esc·F8·숫자 3·중단 버튼은 제어를 대기로 돌립니다. 저장 작업이 이미 시작됐다면 중단 후에도 파일이 생길 수 있으며 결과 경로를 그대로 안내합니다. 실패 후 재시도는 현재 화면을 다시 저장합니다.</p>
<h2>5. 연습과 감도 추천</h2><p><b>연습하기</b>에서는 실제 카메라를 쓰면서도 Chrome 키 입력이나 캡처 파일을 만들지 않습니다. 시작·자세 해제·좌우 쓸기·양손 확대·중단을 연습할 수 있습니다. 카메라가 없다면 명시적인 가상 동작 예시로 흐름만 확인하세요.</p>
<p>감도 추천은 검지를 편 채 정지 5초, 손 펼침을 사이에 둔 왼쪽 10회·오른쪽 10회를 수집합니다. 흔들림·좌우 편차가 크거나 표본이 부족하면 추천을 보류합니다. <b>현재 값과 추천 값을 비교한 뒤 저장 및 적용</b>해야 바뀝니다.</p>
<h2>6. 설정과 문제 확인</h2><p>환경설정에서 카메라·미리보기·쓸기 거리·평활화·양손 집기·저장 폴더·로그 수준을 바꿀 수 있습니다. 카메라 변경 후에는 대기 상태에서 다시 시작하세요. 설정 저장에 실패하면 기존 적용 값과 파일을 유지합니다.</p>
<ul><li>카메라가 보이지 않으면 다른 카메라 번호를 선택하거나 카메라를 사용하는 다른 프로그램을 종료한 뒤 다시 켭니다.</li>
<li>관절은 보이지만 자세가 불명확하면 손 전체와 손바닥이 정면에서 보이게 하고, 검지 외 손가락을 편안히 접으세요. 쓸기 후에는 손을 펼쳐 재무장합니다.</li>
<li>설정과 진단 로그는 <code>%LOCALAPPDATA%/HAND-v2</code>에 있습니다. 로그에는 카메라 영상·Chrome 내용/URL·사용자가 입력한 문자를 저장하지 않습니다.</li>
<li>프로그램 폴더를 옮길 때 EXE 하나만 복사하지 말고 폴더 전체를 복사하세요. Python 설치 없이 실행하도록 묶은 파일이며, 별도 새 PC 검증은 아직 남아 있습니다.</li></ul>
<div class="note">이 빌드는 최종 사용자 확인용 후보입니다. 사람별 손 인식 정확도를 보장하는 수치로 자동 테스트 결과를 읽지 마세요. 실제 검증 범위와 남은 항목은 <a href="release-review.html">검증 보고서</a>에 구분했습니다.</div>'''
(ROOT/'docs/user-guide.html').write_text(document('HAND v2 사용 안내',guide),encoding='utf-8')
readme='''<h1>HAND v2</h1><p>손동작 단축키를 사용하는 Windows 앱의 최종 사용자 확인용 후보입니다. 브라우저 제어, 이미지·발표, 영역 캡처, 환경설정, 연습과 감도 추천을 구현했습니다.</p>
<nav><a href="start_hand.bat">앱 실행</a><a href="dist/HAND-v2-M04-20261117-prepared-swipes/HAND-v2.exe">최신 실행 파일</a><a href="docs/user-guide.html">사용 안내</a><a href="docs/release-review.html">최종 검증 보고서</a></nav>
<h2>시작하기</h2><p>카메라 선택 → 카메라 켜기 → V 0.6초 → 손 펼침 → 동작 가능 → 손동작. 개발 PC의 검증된 장치는 카메라 1입니다. 숫자 3(엄지·검지·중지) 0.35초, F8 또는 중단 버튼으로 멈춥니다.</p>
<h2>검증 범위</h2><p>자동 테스트 __AUTOMATED_TESTS__개 통과. 실제 카메라·모델·Qt 20분, 28,125프레임, 평균 23.44fps, 오류 0, 정상 종료. 현재 150% 배율의 캡처 10개 영역에서 실제 크기와 기준 화면의 모든 픽셀이 일치했습니다.</p>
<div class="note">3명 실손 정확도, 새 Python 없는 PC, 100/125% 실제 화면 배율, 일부 현재 빌드 Chrome 재검증과 명령별 실제 지연 표본은 남아 있습니다. 기능 구현 완료와 모든 배포 게이트 통과는 구분합니다.</div>
<h2>개발 문서</h2><nav><a href="docs/design.html">설계서</a><a href="docs/implementation-plan.html">1 MD 구현 계획</a><a href="docs/progress.html">5 MD 검증·커밋</a><a href="AGENTS.md">개발 원칙</a></nav>
<p>경량 헥사고날·생성자 DI·TDD. source/tests에 실제/가짜 외부 효과를 분리합니다. 소스 공유: <a href="https://github.com/zaa101112-web/hand-v2">GitHub hand-v2</a>. 실행 ZIP은 <a href="https://github.com/zaa101112-web/hand-v2/releases/tag/m08-20261117-rc1">최종 확인용 사전 배포</a>에서 받습니다.</p>
<pre>.venv\\Scripts\\python.exe scripts/validate.py --label local-check
.venv\\Scripts\\python.exe run.py --mode DEV_SIMULATED
.venv\\Scripts\\python.exe scripts/build_windows.py --label local-build</pre>'''
(ROOT/'README.html').write_text(document('HAND v2',readme.replace('dist/HAND-v2-M04-20261117-prepared-swipes/HAND-v2.exe',report.get('build',{}).get('exe','dist/HAND-v2-M04-20261117-prepared-swipes/HAND-v2.exe'))),encoding='utf-8')

mapping={
1:'unit/test_recognition.py',2:'integration/test_final_workflows.py',3:'unit/test_vision_control.py',4:'unit/test_contracts_time.py',5:'integration/test_ui_architecture.py',
6:'unit/test_hand_features.py',7:'unit/test_motion_preparation.py',8:'unit/test_landmark_replay.py',9:'unit/test_windows_input.py',10:'integration/test_windows_ui.py',
11:'unit/test_windows_input.py',12:'integration/test_ui_architecture.py',13:'unit/test_keyboard_worker.py',14:'unit/test_controller.py',15:'unit/test_controller.py',
16:'integration/test_readiness_feedback.py',17:'integration/test_camera_process.py',18:'unit/test_extended_recognition.py',19:'unit/test_controller.py',20:'unit/test_desktop_workspace.py',
21:'integration/test_final_workflows.py',22:'integration/test_image_capture_storage.py',23:'integration/test_desktop_widgets.py',24:'unit/test_images_capture.py',25:'integration/test_image_capture_storage.py',
26:'integration/test_worker_recovery.py',27:'integration/test_worker_recovery.py',28:'unit/test_configuration.py',29:'integration/test_worker_recovery.py',30:'unit/test_gesture_suite.py',
31:'integration/test_ui_architecture.py',32:'integration/test_practice_configuration.py',33:'unit/test_bundle_resources.py',34:None,35:None,36:None,37:None,38:'integration/test_calibration_ui.py',39:'unit/test_controller.py',40:'integration/test_shutdown_watchdog.py'}
notes={2:'자동 + 이전 F8 실기. 현재 빌드 모든 중단 경로의 실손 평가는 별도.',6:'자동 통과, 실손 사람별 표본 미실행.',8:'자동 추적/시간 검증, 좌우 손 실기 표본 미완료.',10:'이전 표시/F8/사용자 STOP 포커스 확인. 계속 버튼 실기 재확인은 남음.',11:'키 배열·충돌·부분 전송 자동. 한/영 환경별 확대 재검증 남음.',17:'실제 카메라 20분 및 프로세스 실패 주입 통과.',19:'자동 + 이전 북마크 창 실기. 현재 빌드 UI 재확인 미완료.',
24:'현재 150%에서 실제 10영역 기준 픽셀 일치.',25:'파일 충돌·손상 PNG·저장 실패 보존 검사. 실제 디스크 부족/모든 파일시스템 오류를 전수 실기한 것은 아님.',27:'100/125/150% 좌표 자동, 실제 150% 10영역. 실제 100/125% 미실행.',33:'새 staging과 번들 시작/소스 해시 검증 결과는 아래 빌드 기록.',34:'NOT_RUN — 별도 Python 없는 Windows 11 PC 필요.',35:'현재 7개 페이지 효과 확인. 나머지는 이전 증거와 구별, URL 안전 중단 이후 결과는 제외.',36:'NOT_RUN — 사용자 요청대로 최종 버전에서만 실손 확인. 3명 정확도 자료 없음.',37:'20분 실제 카메라+Qt PASS, 출력은 가상. 실제 OS 명령별 100회/촬영→키 지연은 미측정.',38:'정지·좌우 표본, 거절, 명시 적용, 원자 저장/실패 보존 자동 검증.',39:'복수 차단 사유와 부분 복구 자동 검증. 모든 실제 하드웨어 동시 오류를 전수 재현한 것은 아님.',40:'막힌 메인 콜백을 별도 프로세스에서 재현해 코드 2 종료. 모든 네이티브/GIL 교착 해결을 보장하지 않음.'}
design=(ROOT/'docs/design.html').read_text(encoding='utf-8');rows=[]
for raw in re.findall(r'<tr[^>]*>(.*?)</tr>',design,re.S):
    cells=re.findall(r'<td[^>]*>(.*?)</td>',raw,re.S)
    if not cells:continue
    name=html.unescape(re.sub('<[^>]+>',' ',cells[0])).strip();match=re.match(r'V2-T(\d\d)',name)
    if not match:continue
    n=int(match.group(1));file=mapping[n]
    evidence=f'<a href="../tests/{file}">관련 자동 시험</a>' if file else '실기 증거 / 외부 게이트'
    rows.append(f'<tr id="V2-T{n:02d}"><td>{html.escape(name)}</td><td>{evidence}</td><td>{html.escape(notes.get(n,"관련 자동 회귀 통과. 전체 시나리오의 실제 사람/하드웨어 검증 완료를 뜻하지 않음."))}</td></tr>')
assert len(rows)==40
audit='''<nav><a href="../README.html">앱 안내</a><a href="user-guide.html">사용법</a><a href="design.html">설계서</a></nav><h1>HAND v2 최종 확인 보고서</h1>
<p>2026-11-17 · 기능 구현 완료 / 최종 사용자 확인용 후보. 계획 5 MD는 작업 범위이며 실제 5일 작업 시간이 아닙니다.</p>
<div class="note"><b>배포 게이트 전체 통과로 표시하지 않습니다.</b> 3명 실손 정확도, 새 PC, 실제 100/125% 배율, 현재 빌드의 남은 Chrome UI와 명령별 지연 측정은 미완료입니다. Computer Use가 새 탭의 URL을 확인하지 못해 중단한 뒤 우회 검증을 진행하지 않았습니다.</div>
<h2>완성한 기능</h2><p>G01–G14 인식과 Chrome 단축키, 이미지 파일/폴더와 슬라이드별 확대, 명시적 영역 캡처/PNG 원자 저장, 설정 저장/복구, 실제 카메라를 쓰는 가상 출력 연습, 표본 기반 감도 추천, 순환 진단 로그, 종료 감시를 연결했습니다. 손 좌표로 OS 포인터를 움직이지 않습니다.</p>
<h2>검증 결과</h2><ul><li><a href="validation/tdd/m08-release-regression.txt">자동 회귀 __AUTOMATED_TESTS__개</a>: 의존 방향·실제/가짜 격리·전체 14동작의 반복 재생 포함.</li>
<li><a href="validation/m07-stability.json">실제 카메라 + Qt 20분</a>: 28,125프레임, 평균 23.44fps, 도착 지연 p95 78ms, 추론 p95 62ms, 오류 0, 정상 종료. 가상 출력으로 실행했으며 실손 정확도나 실제 키까지의 지연 결과가 아닙니다. M07 소스 해시를 보존했고 M08 통합 수정은 영향 범위 자동 검증으로 확인했습니다.</li>
<li><a href="validation/m06-live-capture-baseline.json">실제 캡처 10영역</a>: 현재 150%, 전체 화면·모서리·32px 최소 영역, 실제 PNG 크기와 HAND 표시 전 기준 화면의 모든 픽셀 일치.</li>
<li><a href="validation/m07-chrome-effects-retry.json">현재 Chrome 7개 효과</a>: 뒤로/앞으로·페이지 위/아래·확대/축소·새로고침. 탭 검사 두 항목은 안전 중단 뒤 예약 실행돼 증거에서 제외합니다. <a href="validation/m02-followup.json">이전 탭·북마크·F8 결과</a>와 혼합하지 않습니다.</li></ul>
<h2>5 MD 체크포인트</h2><table><tr><th>범위</th><th>구현·검증</th><th>커밋</th></tr>
<tr><td>M05 D21–25</td><td>이미지·캡처 / 자동 325개 + 실제 캡처</td><td>4e664a2</td></tr>
<tr><td>M06 D26–30</td><td>설정·연습·복구 / 자동 348개 + 캡처 10영역</td><td>d7cd4af</td></tr>
<tr><td>M07 D31–35</td><td>감도·로그 / 자동 354개, 실기 제한 기록</td><td>ba3dc9f</td></tr>
<tr><td>M08 D36–40</td><td>통합 수정·최종 패키징·감사 / 자동 __AUTOMATED_TESTS__개, 외부 게이트 보류</td><td>최종 감사 커밋 참조</td></tr></table>
<h2>빌드와 실행</h2><p><a href="validation/m08-final-bundle-camera.json">최종 EXE의 실제 카메라·모델 시작 및 종료 확인</a>. 진단 로그의 오류 등급 수정도 실패 테스트 후 반영했습니다.</p><p><a href="validation/m08-final.json">최종 기계 판독 보고서</a> · <a href="validation/m08-final-build.json">소스/EXE 해시와 빌드 결과</a> · <a href="validation/m08-final-artifact-manifest.json">동봉 파일 해시</a>. M08 빌드 당시에는 로컬 커밋만 있었습니다. 이후 사용자의 공유 요청에 따른 공개 저장소와 사전 배포 안내는 <a href="../README.md">GitHub 안내</a>를 확인하세요.</p>
<h2>설계 검증 40항목 대응</h2><p>‘관련 자동 시험’은 실제 실행한 파일 연결입니다. 한 파일이 전체 시나리오의 모든 실기 조건을 충족한다는 뜻은 아닙니다. 유지/대체/제외된 원 제안서 항목은 <a href="design.html#decisions">설계서 결정 기록</a>을 따릅니다.</p><table><tr><th>설계 시험</th><th>근거</th><th>범위와 제한</th></tr>'''+''.join(rows)+'</table>'
(ROOT/'docs/release-review.html').write_text(document('HAND v2 최종 확인 보고서',audit),encoding='utf-8')
# Preserve the design as the requirements source, link its historical status to the current audit.
design=design.replace('아래 40개 검증 항목은 <strong>설계한 시험 시나리오</strong>이며 아직 구현·실행하지 않았습니다.',
                      '아래 40개 검증 항목은 <strong>설계한 시험 시나리오</strong>입니다. 현재 구현·검증 범위는 <a href="release-review.html">최종 확인 보고서</a>를 따릅니다.')
design=design.replace('아직 구현·실행하지 않았습니다.','최초 계획의 검증 기준입니다. 최신 구현·검증 범위는 <a href="release-review.html">최종 확인 보고서</a>를 따릅니다.')
def update_row(match):
    row=match.group(0);number=re.search(r'V2-T(\d\d)',row)
    if number and '미실행' in row:
        row=row.replace('<span class="pending">미실행</span>',f'<a href="release-review.html#V2-T{number.group(1)}">최신 검증 범위</a>')
    return row
design=re.sub(r'<tr[^>]*>.*?</tr>',update_row,design,flags=re.S)
(ROOT/'docs/design.html').write_text(design,encoding='utf-8')
progress=ROOT/'docs/progress.html';text=progress.read_text(encoding='utf-8')
if 'id="m05-m08-final"' not in text:
    text=text.replace('<main>','<main><section id="m05-m08-final"><h2>M05–M08 · 최종 사용자 확인용 후보</h2><p>이미지·캡처·설정·연습·감도 추천·로그·종료 처리를 구현했습니다. 자동 __AUTOMATED_TESTS__개, 실제 카메라 20분, 150% 캡처 10영역을 검증했습니다. 사람별 정확도·새 PC 등 외부 게이트는 남아 있습니다. <a href="release-review.html">최신 결과와 40항목 대응표</a> · <a href="user-guide.html">사용 안내</a>. 아래는 이전 체크포인트의 역사적 기록입니다.</p></section>',1)
text=re.sub(r'(id="m05-m08-final".*?자동 )\d+개',lambda m:m.group(1)+str(report['automatic']['passed'])+'개',text,flags=re.S)
progress.write_text(text.replace('__AUTOMATED_TESTS__',str(report['automatic']['passed'])),encoding='utf-8')
plan=ROOT/'docs/implementation-plan.html';text=plan.read_text(encoding='utf-8')
if 'release-review.html' not in text:
    text=re.sub(r'(<main[^>]*>)',r'\1<p class="note">최신 구현·검증 상태: <a href="release-review.html">M05–M08 최종 확인 보고서</a>. D35/D36 사람별 평가와 D39 새 PC 검증은 사용자 최종 확인/외부 환경 게이트로 남겨두었습니다.</p>',text,count=1)
text=re.sub(r'<tr[^>]*>.*?</tr>',update_row,text,flags=re.S)
plan.write_text(text,encoding='utf-8')
print('Wrote user guide, release audit, README, and links to current verification.')
