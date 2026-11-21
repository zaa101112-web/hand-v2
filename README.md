# HAND v2

손동작을 인식해 Chrome 단축키를 실행하는 Windows 앱입니다. 이미지·발표, 영역 캡처, 환경설정, 연습과 감도 추천을 지원합니다. 손 좌표로 마우스를 움직이지 않습니다.

**현재 버전은 최종 사용자 확인용 후보입니다.** 자동 테스트 통과가 사람별 손 인식 정확도 검증 완료를 뜻하지는 않습니다.

## M09 연속 동작 변경

이 브랜치는 양손 집기를 유지한 연속 확대·축소와 검지/V 동작 끝의 준비 멈춤을 지원합니다. 매번 손을 펼칠 필요가 없습니다. 연습 화면에 8과제/10단계 측정과 결과 JSON 복사를 추가했습니다. [변경·검증 안내](docs/continuous-review.html)에서 합성 240단계 결과와 실손 미실행 항목을 구분합니다. 기존 GitHub Release는 아래 M08이며 이번 변경은 포함하지 않습니다.

소스로 실행하려면 clone 후 `git switch codex/continuous-gestures`를 사용하세요.

## 기존 M08 앱을 공유하려면

1. [실행 파일 다운로드 페이지](https://github.com/zaa101112-web/hand-v2/releases/tag/m08-20261117-rc1)를 엽니다.
2. Assets의 **HAND-v2-M08-20261117-r2.zip**을 받습니다. `Source code (zip)`은 개발용 소스입니다.
3. 압축을 모두 풀고 **HAND-v2.exe**를 실행합니다. `_internal` 폴더도 함께 있어야 합니다.
4. 카메라를 선택하고 **카메라 켜기 → V 0.6초 → 손 펼침 → 동작 가능** 순서로 시작합니다. 카메라 번호는 PC마다 다릅니다.
5. Chrome 창을 앞에 두고 본문을 한 번 클릭한 뒤 손동작을 합니다. 매 동작 후 손을 펼쳐 다시 준비합니다.

중단은 **F8**, **숫자 3(엄지·검지·중지) 0.35초**, 또는 **중단 버튼**입니다. F8 등록 실패 여부는 앱 상단에 표시됩니다.

ZIP 안의 **사용안내.html**에 이미지·캡처·연습·설정 사용법이 있습니다. Python을 따로 설치하지 않고 실행하도록 묶었지만, 독립된 새 PC에서의 전체 검증은 아직 남아 있습니다.

## 손동작과 Chrome 단축키

| 손동작 | 기능 | 단축키 |
| --- | --- | --- |
| 검지 왼쪽 / 오른쪽 쓸기 | 뒤로 / 앞으로 | Alt + ← / → |
| V 왼쪽 / 오른쪽 쓸기 | 이전 / 다음 탭 | Ctrl + Shift + Tab / Ctrl + Tab |
| V 위 / 아래 쓸기 | 페이지 위 / 아래 | Page Up / Page Down |
| 양손 엄지·검지 집기 후 간격 벌리기 / 좁히기 | 한 단계 확대 / 축소 | Ctrl + 숫자패드 + / − |
| 검지로 원 그리기 | 새로고침 | Ctrl + R |
| 엄지 0.6초 유지 | 북마크 창 | Ctrl + D |
| 주먹 0.25초 → 1.2초 안에 펼침 | 닫은 탭 복구 | Ctrl + Shift + T |
| 양손 L 0.8초 유지 | 앱의 영역 캡처 시작 | 앱 내부 기능 |

뒤로/앞으로는 방문 기록이 있는 탭에서 확인하세요. 북마크 창을 닫은 뒤 작은 상태창에서 **계속**을 누르고 손을 펼쳐야 다음 명령을 실행합니다. 캡처 영역은 실제 마우스나 키보드로 선택하고 Enter로 저장합니다.

## 코드를 함께 개발하려면

Windows 11 x64와 Python 3.12를 기준으로 개발했습니다. 저장소에는 모델과 기본 설정이 포함되어 있습니다.

```powershell
git clone https://github.com/zaa101112-web/hand-v2.git
cd hand-v2
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe run.py --camera 0
```

```powershell
# 실제 입력을 보내지 않는 개발 화면
.venv\Scripts\python.exe run.py --mode DEV_SIMULATED

# 자동 회귀 검사
.venv\Scripts\python.exe scripts/validate.py --label local-check

# 독립된 staging 폴더에 Windows 실행 파일 빌드
.venv\Scripts\python.exe scripts/build_windows.py --label local-build
```

개발할 때 [개발 원칙](AGENTS.md), [설계서](docs/design.html), [1 MD 구현 계획](docs/implementation-plan.html)을 먼저 참고합니다. HTML 문서는 내려받아 브라우저로 열면 원래 레이아웃으로 볼 수 있습니다. 경량 헥사고날·생성자 의존성 주입·TDD를 적용하며 5 MD 범위별 검증 커밋을 보존했습니다.

## 확인한 범위

- 자동 회귀 **363개 통과**.
- 실제 카메라·모델·Qt 20분: 28,125프레임, 평균 23.44fps, 카메라 오류 0건, 정상 종료. 이 검사의 명령 출력은 가상입니다.
- 최종 EXE의 실제 카메라·모델 시작과 정상 종료 확인.
- 현재 Windows 150% 배율에서 캡처 10영역의 크기와 기준 화면 픽셀 일치.
- 3명 실손 정확도, 새 PC, 실제 100/125% 배율, 명령별 실제 지연 및 일부 현재 Chrome UI 재검증은 남아 있습니다.

[상세 검증 보고서](docs/release-review.html) · [기계 판독 결과](docs/validation/m08-final.json) · [공유 배포 설명](docs/sharing-release-notes.md)

설정과 진단 로그는 `%LOCALAPPDATA%/HAND-v2`에 저장됩니다. 사용자 설정·카메라 영상·로컬 가상환경·배포 ZIP은 소스 Git에 포함하지 않습니다. 실행 ZIP은 GitHub Releases에서 제공합니다.
