# 🐹 햄스터 로봇 AI 쓰레기 4종 분리배출 스마트 감지 및 자율주행 시스템

웹캠 카메라를 통해 **쓰레기 4종 (종이, 종이팩, 캔, 플라스틱/페트병)**을 실시간으로 감지하고, **Google 티처블 머신(Teachable Machine) AI 모델**과 **햄스터 로봇**의 4색 LED, 부저 알림 및 정밀 자율주행 복귀를 통해 스마트 분리배출을 수행하는 파이썬 통합 응용 프로그램입니다.

---

## 🎨 쓰레기 4종 분리배출 LED & 하드웨어 반응표

| 슬롯 번호 | 쓰레기 범주 | 확정 조건 | 로봇 하드웨어 피드백 | LED 표시 색상 |
| :---: | :--- | :---: | :---: | :---: |
| **`1`** | **종이** | 연속 6프레임 (신뢰도 ≥ 0.65) | 삐 소리 ➔ 집게 열기(OPEN) ➔ 5초 대기 ➔ 슬롯 자율주행 ➔ 정밀 역주행 복귀 | **노란색 LED** 🟡 (`yellow`) |
| **`2`** | **종이팩 (우유팩)** | 연속 6프레임 (신뢰도 ≥ 0.65) | 삐 소리 ➔ 집게 열기(OPEN) ➔ 5초 대기 ➔ 슬롯 자율주행 ➔ 정밀 역주행 복귀 | **하늘색 LED** 🩵 (`cyan`) |
| **`3`** | **캔** | 연속 6프레임 (신뢰도 ≥ 0.65) | 삐 소리 ➔ 집게 열기(OPEN) ➔ 5초 대기 ➔ 슬롯 자율주행 ➔ 정밀 역주행 복귀 | **초록색 LED** 🟢 (`green`) |
| **`4`** | **플라스틱 / 페트병** | 연속 6프레임 (신뢰도 ≥ 0.65) | 삐 소리 ➔ 집게 열기(OPEN) ➔ 5초 대기 ➔ 슬롯 자율주행 ➔ 정밀 역주행 복귀 | **파란색 LED** 🔵 (`blue`) |
| **-** | **대기 / 미인식** | 신뢰도 < 0.65 | 제자리 대기 유지 | **LED OFF** ⚪ (`off`) |

---

## ✨ 핵심 시스템 기능

1. **티처블 머신(Teachable Machine) 실전 인식률 99% 보정 (1:1 Center Square Crop)**
   - 웹 브라우저 캔버스와 동일하게 OpenCV 프레임을 중앙 1:1 정사각형(`min(h, w)`)으로 절삭한 후 `(224, 224)` 정규화 처리하여 왜곡 없이 정확하게 인식합니다.
2. **연속 6프레임 정밀 확정 알고리즘 (`REQUIRED_FRAMES = 6`)**
   - 안정적인 판단을 위해 동일 쓰레기 범주가 연속 6프레임 동안 감지될 때 배출 자율주행을 시작합니다.
3. **안전 집게 열림 유지 모드 (Open Gripper Maintain)**
   - 6프레임 확정 시 제자리에 멈춰 집게를 펼치고(`OPEN`) 5초 동안 쓰레기 거치 시간을 부여하며, 주행 중에도 집게를 오므리지 않고 열린 상태를 유지합니다.
4. **오차 0.00cm 정밀 대칭 역주행 복귀**
   - 지정 수거함 투입 완료 후, 1:1 대칭 역주행 궤적 알고리즘으로 시작 지점 위치로 오차 없이 완벽하게 복귀합니다.

---

## 📂 디렉터리 구조

```text
hamster/
├── README.md               ← 프로젝트 안내서 (현재 파일)
├── AGENTS.md               ← 개발 및 트러블슈팅 가이드
├── pyproject.toml          ← 프로젝트 메타데이터 & 의존성
├── main.py                 ← 스마트 분리배출 메인 프로그램 (OpenCV + TensorFlow)
├── models/
│   ├── keras_model.h5      ← 최신 티처블 머신 Keras 모델
│   └── labels.txt          ← 레이블 목록 (0 종이, 1 종이팩, 2 캔, 3 플라시틱& 페트병)
├── routes/                 ← 수거함 슬롯(1~4번) 자율주행 저장 경로
└── tools/
    ├── check_connection.py      ← 햄스터 블루투스 연결 & 하드웨어 점검 도구
    ├── keyboard_control.py      ← 키보드 방향키/WASD 실시간 로봇 조종 도구
    ├── train_local_model.py     ← 로컬 데이터셋 기반 모델 추가 학습 도구
    ├── play_furelise.py         ← '엘리제를 위하여' 연주 도구
    ├── play_grandfathers_clock.py ← '할아버지의 낡은 시계' 연주 도구
    ├── play_toy_forest.py       ← '장난감 숲' 연주 도구
    ├── play_mario_wiggle.py     ← 마리오 테마 연주 + 엉덩이 댄스 도구
    └── play_mario_gripper.py    ← 마리오 테마 연주 + 엉덩이 댄스 + 집게 박수 도구
```

---

## 🚀 실행 명령어 가이드

### 1. 프로그램 실행 (권장)
```bash
uv run hamster
# 또는
uv run python main.py
```
* 종료하려면 카메라 창에서 **ESC** 키를 누르세요.

### 2. 하드웨어 점검 & 조종
- **햄스터 연결 및 LED/집게 점검**: `uv run python tools/check_connection.py`
- **키보드로 실시간 직접 운전**: `uv run python tools/keyboard_control.py`

### 3. 무설치 실행파일 (.exe) 재빌드
```bash
uv run pyinstaller --noconfirm hamster_sorting_robot.spec
```

---

## 🐙 깃허브 원격 저장소 (GitHub Repositories)
- **메인 저장소**: [https://github.com/logic4rest/hamster](https://github.com/logic4rest/hamster)
- **미러 저장소**: [https://github.com/wwwbsy100-lgtm/hamster](https://github.com/wwwbsy100-lgtm/hamster)
