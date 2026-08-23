# 🐹 햄스터 로봇 AI 스마트 분리배출 개발 및 제작 가이드

본 폴더(`제작/`)는 **다른 개발자나 사용자, AI 코딩 어시스턴트가 이 프로젝트와 동일한 고성능 햄스터 로봇 AI 시스템을 쉽게 구축하고 수정/확장**할 수 있도록 준비된 개발자용 종합 가이드 패키지입니다.

---

## 📂 `제작/` 폴더 구성 요소

| 파일명 | 설명 |
| :--- | :--- |
| **`README.md`** | 현재 개발 및 시스템 구조 전체 가이드서 |
| **`AI_PROMPTS_AND_RULES.md`** | AI(Gemini, ChatGPT 등)에게 개발 지시를 내릴 때 쓰는 프롬프트 모음 |
| **`starter_template.py`** | 누구나 쉽게 따라 작성할 수 있는 햄스터 로봇 모듈화 스타터 템플릿 |
| **`build_exe_standalone.bat`** | 파이썬 미설치 PC용 윈도우 `.exe` 독립 실행 파일 1초 빌드 스크립트 |
| **`run_developer_mode.bat`** | 개발자 모드 즉시 실행 스크립트 |

---

## 🛠️ 1. 개발 환경 구축 (3분 완벽 설치)

### [권장] `uv` 패키지 매니저 사용 시
```bash
# 1. 의존성 패키지 동기화 설치
uv sync

# 2. 메인 AI 스마트 분리배출 시스템 실행
uv run python main.py
```

### 일반 `pip` 사용 시
```bash
pip install roboid opencv-python tensorflow tf-keras pillow keyboard numpy flask qrcode pyinstaller
python main.py
```

---

## ⚙️ 2. 핵심 시스템 동작 원리 (개발 핵심)

### 1) AI 재활용품 감지 신뢰도 & 6프레임 확정 알고리즘
- **신뢰도 기준**: `CONFIDENCE_THRESHOLD = 0.8` (80% 미만은 안전 대기)
- **연속 프레임 필터**: `REQUIRED_FRAMES = 6` (동일 쓰레기가 연속 6프레임 감지되어야 최종 확정)

### 2) 4초 거치 대기 & 집게 제어 시퀀스
1. 연속 6프레임 분석 완료 시 "삐!" 알림음 발생.
2. 제자리에 멈춰 **집게를 열고(`OPEN`) 4초간 거치 대기** (`WAIT_PLACEMENT_SEC = 4.0`).
3. 4초 후 **집게를 닫아(`CLOSE`) 쓰레기 포획**.
4. 포획 완료 후 지정된 수거함 슬롯(1~4번)으로 자율주행 이동.
5. 수거함 도착 시 집게를 열어 쓰레기 투입 후 **0.00cm 대칭 역주행 궤적 엔진**으로 시작점 정밀 복귀!

### 3) 햄스터 로봇 쓰레기 4종/5종 LED 안내표
- **플라스틱 / 페트병**: 🔵 파란색 LED (`blue`)
- **캔**: 🟢 초록색 LED (`green`)
- **종이**: 🟡 노란색 LED (`yellow`)
- **종이팩(우유팩)**: ⚪ 하늘색/흰색 LED (`white`)
- **경고 / 이물질**: 🔴 빨간색 LED (`red`)

---

## 📦 3. Windows 독립 실행 파일 (.exe) 빌드

다른 사람에게 프로그램만 전달하여 실행하게 하려면 아래 명령어를 실행하거나 `build_exe_standalone.bat`를 더블클릭하세요:

```bash
uv run pyinstaller hamster_sorting_robot.spec
```
- 생성 파일 위치: `dist/hamster_sorting_robot/hamster_sorting_robot.exe`

---

## 🌐 4. 스마트폰 QR 관제센터 & 2D 시뮬레이터 연동

`main.py` 실행 시 백그라운드 웹서버가 자동으로 포트 `5000`에서 켜집니다:
- **로컬 관제 사이트**: `http://192.168.219.105:5000`
- **온라인 웹사이트 (GitHub Pages)**: `https://logic4rest.github.io/hamster/`
- **소스코드 ZIP 원터치 다운로드**: `http://192.168.219.105:5000/download`
