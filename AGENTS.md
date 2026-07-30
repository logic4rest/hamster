# AGENTS.md — 햄스터 봇 손모양 조종 프로젝트

> AI 에이전트 및 기여자를 위한 프로젝트 안내서입니다.  
> 처음 실행이 안 될 때는 **[❌ 흔한 문제 해결](#-흔한-문제-해결)** 섹션을 먼저 확인하세요.

---

## 📌 프로젝트 개요

웹캠으로 **가위 / 바위 / 보** 손모양을 인식하고, [Google 티처블 머신](https://teachablemachine.withgoogle.com) 으로 학습시킨 Keras 모델을 이용해 **햄스터 로봇**을 실시간으로 제어하는 파이썬 프로그램입니다.

| 손모양 | 로봇 동작 |
|--------|-----------|
| ✌️ 가위 | 전진 |
| ✊ 바위 | 후진 |
| 🖐 보   | 정지 |
| 인식 없음 / 신뢰도 부족 | 정지 (안전) |

---

## 🗂️ 디렉터리 구조

```
hamster/
├── AGENTS.md              ← 이 파일
├── README.md
├── pyproject.toml         ← 프로젝트 메타데이터 & 의존성
├── main.py                ← 독립 실행 스크립트 (opencv + tensorflow 직접 사용)
├── hamster/
│   ├── __init__.py
│   └── __main__.py        ← 패키지 진입점 (roboidai 방식, 권장)
├── models/
│   ├── keras_model.h5     ← 티처블 머신에서 내려받은 Keras 모델 ⚠️ 직접 준비 필요
│   └── labels.txt         ← 클래스 레이블 목록 ⚠️ 직접 준비 필요
├── tools/
│   ├── check_connection.py  ← 연결 확인 & 하드웨어 점검 스크립트
│   └── keyboard_control.py  ← 방향키 / WASD 키보드 조종 스크립트
└── docs/
    ├── 16차시-손모양-인식-티처블머신.md
    └── ...                ← 차시별 수업 자료
```

> ⚠️ `models/keras_model.h5` 와 `models/labels.txt` 는 저장소에 포함되지 않습니다.  
> 아래 **[모델 준비](#-모델-준비-티처블-머신)** 단계를 따라 직접 생성하세요.

---

## ⚙️ 환경 요구사항

| 항목 | 권장 사양 |
|------|-----------|
| OS | Windows 10/11 (64-bit) |
| Python | 3.11 이상 |
| 패키지 관리 | `uv` (권장) 또는 `pip` |
| 하드웨어 | 햄스터 로봇 S + BLE USB 동글 |
| 카메라 | USB 웹캠 (내장 카메라 포함) |

---

## 🚀 빠른 시작

### 1단계 — 저장소 클론 & 이동

```bash
git clone <저장소-URL>
cd hamster
```

### 2단계 — 의존성 설치

**uv 사용 (권장)**
```bash
pip install uv          # uv가 없다면 먼저 설치
uv sync
```

**pip 사용**
```bash
pip install -e .
# 또는 라이브러리만 개별 설치
pip install -U roboid roboidai mediapipe opencv-python
```

### 3단계 — 모델 준비 (티처블 머신)

1. [teachablemachine.withgoogle.com](https://teachablemachine.withgoogle.com) 접속 → **Get Started** → **Image Project**
2. 클래스 3개 생성: `가위` / `바위` / `보`
3. 각 클래스에 웹캠 사진 수십 장씩 업로드
4. **Train Model** 클릭 → 학습 완료 후 **Export Model**
5. **Tensorflow** 탭 → **Keras** 선택 → **Download my model**
6. 다운로드된 `converted_keras.zip` 압축 해제
7. 파일 두 개를 이 프로젝트의 `models/` 폴더에 복사:
   ```
   models/
   ├── keras_model.h5
   └── labels.txt
   ```

> `labels.txt` 예시 (클래스명이 한글이어야 합니다):
> ```
> 0 가위
> 1 바위
> 2 보
> ```

### 4단계 — 햄스터 연결

1. BLE USB 동글을 PC에 꽂는다.
2. 햄스터 로봇 전원을 켠다.
3. 로봇이 동글과 자동 페어링될 때까지 기다린다 (LED 깜빡임 → 점등).

### 5단계 — 실행

**패키지 방식 (권장)**
```bash
uv run hamster
# 또는
python -m hamster
```

**독립 스크립트 방식**
```bash
python main.py
```

실행 후 카메라 창이 열리고 **2초 카운트다운** 뒤 손모양 인식이 시작됩니다.  
종료하려면 카메라 창에서 **ESC** 키를 누르세요.

---

## 🛠️ 보조 도구 (tools/)

### check_connection.py — 연결 & 하드웨어 점검

처음 실행하거나 로봇이 안 움직일 때 **가장 먼저** 실행하세요.  
LED · 소리 · 바퀴 동작을 단계별로 자동 점검합니다.

```bash
python tools/check_connection.py
uv run python tools/check_connection.py
```

점검 순서:
1. roboid 라이브러리 임포트
2. 햄스터 BLE 연결
3. LED (빨강 → 파랑 → 초록)
4. 부저 (삐~ 소리)
5. 바퀴 (전진 → 후진 → 좌회전 → 우회전)

---

### keyboard_control.py — 키보드 조종

손모양 인식 없이 **키보드만으로** 실시간 조종합니다.  
실행 전 `keyboard` 라이브러리가 필요합니다:

```bash
pip install keyboard   # 또는 uv sync (pyproject.toml 에 이미 추가됨)
```

```bash
python tools/keyboard_control.py
uv run python tools/keyboard_control.py
```

| 키 | 동작 |
|----|------|
| `W` / `↑` | 전진 |
| `S` / `↓` | 후진 |
| `A` / `←` | 제자리 좌회전 |
| `D` / `→` | 제자리 우회전 |
| `W`+`A` / `↑`+`←` | 전진하며 좌로 꺾기 |
| `W`+`D` / `↑`+`→` | 전진하며 우로 꺾기 |
| `S`+`A` / `↓`+`←` | 후진하며 좌로 꺾기 |
| `S`+`D` / `↓`+`→` | 후진하며 우로 꺾기 |
| `Space` | 강제 정지 |
| `Q` / `ESC` | 프로그램 종료 |

> **팁**: 키에서 손을 떼면 자동으로 정지합니다.

---

## 🎓 모델 학습 팁


| 항목 | 권장 사항 |
|------|-----------|
| 클래스당 이미지 수 | 최소 50장, 100장 이상 권장 |
| 배경 다양성 | 여러 배경에서 촬영해야 과적합 방지 |
| 손 크기 | 화면의 50~70% 정도 채우기 |
| 조명 | 너무 어둡거나 역광이면 인식률 하락 |
| 클래스 불균형 | 각 클래스 이미지 수를 비슷하게 맞출 것 |

---

## 🔧 주요 설정값 (`hamster/__main__.py` 및 `main.py`)

```python
CONFIDENCE_THRESHOLD = 0.7   # 인식 신뢰도 기준 (0.0 ~ 1.0)
                              # 값을 낮추면 더 쉽게 인식, 오인식 가능성 증가
WHEEL_SPEED          = 50    # 바퀴 속도 (-100 ~ 100)
COUNTDOWN_SEC        = 2     # 시작 전 카운트다운 (초)
```

---

## ❌ 흔한 문제 해결

### 🔴 "카메라를 열 수 없습니다" / 카메라 창이 안 뜰 때

- 다른 앱(Zoom, 카카오톡 등)이 카메라를 점유 중인지 확인하고 닫는다.
- `main.py` 에서 카메라 인덱스를 변경해 본다:
  ```python
  cap = cv2.VideoCapture(1)  # 0 → 1 로 변경
  ```
- `hamster/__main__.py` 에서:
  ```python
  cam = ai.Camera('usb1', flip='h', square=True)  # usb0 → usb1
  ```

### 🔴 햄스터가 연결되지 않을 때

- BLE 동글이 올바른 USB 포트에 꽂혀 있는지 확인한다.
- 햄스터 로봇 전원이 켜져 있는지 확인한다.
- 장치 관리자에서 동글 드라이버가 정상 인식되는지 확인한다.
- 한 번에 하나의 햄스터만 연결되어 있어야 한다.
- 프로그램을 완전히 종료한 뒤 동글을 뽑았다 다시 꽂고 재실행한다.

### 🔴 `ModuleNotFoundError: No module named 'roboid'`

```bash
pip install -U roboid roboidai
```

### 🔴 `ModuleNotFoundError: No module named 'tf_keras'` / Keras 모델 로드 오류

```bash
pip install tf-keras
```

또는 `main.py` 의 `load_model()` 함수가 자동으로 패치를 시도합니다.  
`hamster/__main__.py` (roboidai 방식)는 내부적으로 호환 로더를 사용하므로 이 오류가 없습니다.

### 🔴 `FileNotFoundError: models/keras_model.h5`

`models/` 폴더에 티처블 머신 모델 파일이 없습니다.  
위의 **[모델 준비](#-모델-준비-티처블-머신)** 단계를 따라 파일을 준비하세요.

### 🔴 인식은 되는데 로봇이 안 움직일 때

1. `labels.txt` 의 레이블 이름이 정확히 `가위` / `바위` / `보` 인지 확인한다 (공백, 오탈자 주의).
2. 신뢰도 기준(`CONFIDENCE_THRESHOLD`)이 너무 높지 않은지 확인한다 (기본값 `0.7`).
3. 터미널에 `[인식]` 로그가 출력되는지 확인한다 — 출력된다면 로봇 연결 문제이다.
4. 햄스터 배터리가 충분한지 확인한다.

### 🔴 손모양 인식이 잘 안 될 때

- 조명을 밝게 하고 배경을 단순하게 만든다.
- 손이 화면 중앙에 크게 오도록 위치를 조정한다.
- 학습 데이터를 더 많이 수집하고 모델을 재학습한다.
- `CONFIDENCE_THRESHOLD` 를 `0.6` 으로 낮춰 본다.

### 🔴 `tmi.detect()` 오류 (교재 코드 사용 시)

교재 268–269p 예제는 `tmi.detect()`를 사용하나, 실제 API는 `tmi.predict()`입니다.  
오류 발생 시 `detect` → `predict` 로 변경하세요.

---

## 🤖 AI 에이전트를 위한 안내

이 저장소를 작업하는 AI 에이전트는 아래 사항을 준수하세요:

### 코드 수정 시 주의사항
- `hamster/__main__.py` — **권장 실행 경로** (roboidai 방식). 이 파일 우선 수정.
- `main.py` — 레거시 독립 스크립트 (opencv + tensorflow 직접 사용). 별도 유지보수.
- `models/` 폴더 내 파일은 `.gitignore` 대상이므로 커밋하지 않는다.
- 레이블 비교는 반드시 한글(`가위`, `바위`, `보`, `없음`)로 작성한다.

### 테스트 방법
- 실제 하드웨어 없이 로직 테스트 시, `Hamster()` 를 Mock 객체로 대체한다.
- 카메라 없이 테스트 시, `cv2.VideoCapture` 에 영상 파일 경로를 전달한다.

### 의존성 추가 시
```bash
uv add <패키지명>       # pyproject.toml 자동 업데이트
# 또는
pip install <패키지명>  # pyproject.toml 에 수동으로 추가 필요
```

---

## 📚 참고 자료

- 교재: `docs/파이썬으로-배우는-햄스터와-인공지능_ver240619.pdf`
- 16차시 수업 자료: [`docs/16차시-손모양-인식-티처블머신.md`](docs/16차시-손모양-인식-티처블머신.md)
- [roboid 공식 문서](https://roboidai.readthedocs.io)
- [Google 티처블 머신](https://teachablemachine.withgoogle.com)
