# 번외 — 자율주행(햄스터AI카메라 활용)

> 출처: [파이썬으로 배우는 햄스터와 인공지능 (ver240619)](파이썬으로-배우는-햄스터와-인공지능_ver240619.pdf) PDF 270–288쪽

햄스터에 부착하는 별매 부품인 **햄스터 AI 카메라**(외장 카메라)로 바닥의 트랙(초록색·파란색 선)을 인식해 차선을 따라 자율주행하고, 티처블 머신으로 학습한 속도 표지판(30/70)까지 인식해 속도를 바꾸는 실습이다.

---

## 01 영상처리 관련 클래스, 메소드 안내 (271–274p)

### 트랙 검출 — roboidai.lab 모듈의 함수

| 함수 | 설명 |
|---|---|
| `find_track_xy(image, output, color, hrange, srange=(50,255), vrange=(50,255), window_height=-1, min_area=0)` | 영상에서 h, s, v 범위에 해당하는 Blob을 찾아 무게 중심을 반환한다. `image`: 입력 영상. `output`: 결과를 표시할 영상. `color`: 결과를 표시할 색깔(B, G, R). `hrange`: Hue의 범위(최소, 최대), 범위가 2개면 (최소1, 최대1, 최소2, 최대2). `srange`: Saturation의 범위. `vrange`: Value의 범위. `window_height`: 초록색·파란색 선을 검출하는 영상 부분의 세로 방향 높이, 영상 제일 아래에서 이 높이만큼의 영상에서 선을 검출함(-1이면 영상 전체 사용). `min_area`: 발견된 Blob의 넓이가 이보다 작으면 Blob으로 인정하지 않음. 반환 값: `(x, y)` 튜플(무게 중심 좌표) |
| `find_green_track_xy(image, output, h_range=(40,80), s_range=(50,255), v_range=(50,255), window_height=-1, min_area=0)` | 영상에서 초록색 Blob을 찾아 무게 중심을 반환한다. |
| `find_blue_track_xy(image, output, h_range=(100,140), s_range=(50,255), v_range=(50,255), window_height=-1, min_area=0)` | 영상에서 파란색 Blob을 찾아 무게 중심을 반환한다. |
| `find_red_track_xy(image, output, h_range=(0,10,170,180), s_range=(50,255), v_range=(50,255), window_height=-1, min_area=0)` | 영상에서 빨간색 Blob을 찾아 무게 중심을 반환한다. |

---

## 02 자율주행 (275–282p)

### 준비물

- 활동지(초록색 안쪽 선 + 파란색 바깥쪽 선으로 그려진 타원형 트랙)
- 햄스터 AI 카메라

### 카메라 설치 (받침대 활용 시)

- 카메라 받침대를 햄스터 로봇의 앞쪽 끝에 부착하고 뒤쪽 아래로 기울인다.
- 카메라가 뒤쪽 아래를 바라보도록 카메라를 카메라 받침대에 부착한다.
- 카메라가 삐뚤지 않게 한다.

### 로봇 배치

햄스터 로봇을 활동지에 올려 놓는다. 반시계 방향으로 이동한다. **후진으로 주행하므로 거꾸로 놓아야 한다.**

### 원리 — 좌우 선까지의 거리 차이로 조향하기

차이 = 오른쪽 거리 − 왼쪽 거리. 차이를 기존 주행 속도에 더하고(왼쪽 바퀴), 빼면(오른쪽 바퀴), 차이가 커질수록 왼쪽 바퀴의 속도가 오른쪽보다 빨라져 오른쪽으로 회전하는 형태로 주행하게 된다. 반대로 차이가 음수(왼쪽 거리 > 오른쪽 거리)이면 왼쪽으로 회전하는 형태로 주행한다.

카메라 화면의 세로 방향 아래쪽 일부 구간(`window_height`)에서 초록색 선(`left_x`)과 파란색 선(`right_x`)의 x좌표를 찾고, 화면 중심(`center_x`)까지의 절대 거리를 각각 계산해 그 차이만큼 좌우 바퀴 속도를 보정한다.

### 자율 주행 코드

```python
from roboid import *
import roboidai as ai
import roboidai.lab as lab

cam = ai.Camera('ip0')  # 외장 카메라로 사용한다.
hamster = HamsterS()

velocity = -70  # 후진 주행이 원칙이므로 기본 속도를 음수로 설정한다. 양수를 입력하면 전진합니다.

def control_hamster(center_x, left_x, right_x):
    # 매개변수는 화면의 중심선, 왼쪽 선, 오른쪽 선
    left_dist = abs(center_x - left_x)  # 화면 중심 선과 왼쪽에서 인식 되는 선 사이의 절대거리
    right_dist = abs(center_x - right_x)  # 화면 중심 선과 오른쪽에서 인식 되는 선 사이의 절대 거리
    diff = right_dist - left_dist  # 오른쪽 거리와 왼쪽 거리의 "차이"를 diff에 저장
    hamster.wheels(velocity + 0.1*diff, velocity - 0.1*diff)
    # 왼쪽 바퀴와 오른쪽 바퀴의 속도를 -70에서 차이의 10%만 추가하여 설정한다.

while True:
    image = cam.read()
    if image is not None:
        width = image.shape[1]
        height = image.shape[0]
        output = image.copy()

        left_x, _ = lab.find_green_track_xy(image, output, window_height=50)
        # 영상에서 초록색 Blob을 찾아 무게중심을 반환합니다.
        right_x, _ = lab.find_blue_track_xy(image, output, window_height=50)
        # 영상에서 파란색 Blob을 찾아 무게중심을 반환합니다.
        if left_x < 0: left_x = 0
        # 초록색 Blob의 무게중심이 음수면 0으로 초기화
        if right_x < 0: right_x = width
        # 파란색 Blob의 무게중심이 음수면 width로 초기화
        control_hamster(width//2, left_x, right_x)
        # 함수 실행
        cam.show(output)
        if cam.check_key(10) == 'esc': break

hamster.stop()
wait(500)
```

로봇이 너무 흔들리면 보정 비율(코드의 `0.1`)을 더 작은 값으로 줄인다.

---

## 속도 감지 자율 주행 자동차 (283–287p)

바깥쪽 트랙에 속도 30/70 표지판을 붙여 두고, 햄스터가 그 표지판을 인식하면 주행 속도를 바꾸는 자율주행 자동차를 만든다.

**준비물**: 활동지(트랙 + 속도 30 시그널 + 속도 70 시그널), 햄스터 AI 카메라

**이미지 학습**: 16차시의 티처블 머신 사용법을 참고해 직접 훈련한 모델을 사용한다. 학습시킬 이미지: 트랙, 속도 30 시그널, 속도 70 시그널.

```python
from roboid import *
import roboidai as ai
import roboidai.lab as lab

cam = ai.Camera('ip0')  # 외장 카메라 사용
hamster = HamsterS()

tmi = ai.TmImage()  # 티처블 머신 이미지 프로젝트 객체 생성
tmi.load_model('c:/Example/speed')
# 티처블 머신에서 다운로드하여 압축을 푼 모델 파일(keras_model.h5, labels.txt)이 있는 폴더
velocity = -50  # 후진 주행이 원칙이므로 기본 속도를 음수로 설정한다.
VEL_LOW = -30
VEL_HIGH = -70

def control_hamster(center_x, left_x, right_x):
    left_dist = abs(center_x - left_x)
    right_dist = abs(center_x - right_x)
    diff = right_dist - left_dist
    hamster.wheels(velocity + 0.1*diff, velocity - 0.1*diff)

cam.count_down(3)
candidates = []
while True:
    image = cam.read()
    if image is not None:
        width = image.shape[1]  # 햄스터 카메라는 320x640의 이미지 크기
        height = image.shape[0]
        output = image.copy()

        left_x, _ = lab.find_green_track_xy(image, output, window_height=50)
        # 영상에서 초록색 Blob을 찾아 무게중심을 반환합니다.
        right_x, _ = lab.find_blue_track_xy(image, output, window_height=50)
        # 영상에서 파란색 Blob을 찾아 무게중심을 반환합니다.
        _, red_y = lab.find_red_track_xy(image, output, min_area=1000)
        # 빨간 색 stop 시그널은 빨간 색 물체 인식의 y좌표를 사용합니다.
        # min_area인 1000보다 작으면 인정하지 않습니다.
        if left_x < 0: left_x = 0
        if right_x < 0: right_x = width

        if red_y > height // 2:
            if tmi.predict(image):
                label = tmi.get_label()
                if label == '30':
                    candidates.append(VEL_LOW)  # 인식된 label이 30일 때 VEL_LOW를 candidates에 추가
                elif label == '70':
                    candidates.append(VEL_HIGH)  # 인식된 label이 70일 때 VEL_HIGH를 candidates에 추가
            elif len(candidates) > 0:
                print(candidates)
                # elif문에서 추가한 candidates 리스트를 가지고 속도를 바꾸기 때문에
                # red_y > height//2가 만족되는 동안에는 계속 기본 속도로 주행하게 됩니다.
                velocity = VEL_HIGH if candidates.count(VEL_HIGH) > candidates.count(VEL_LOW) else VEL_LOW
                # candidates의 원소 중 VEL_HIGH가 VEL_LOW의 수 보다 많을 경우 속도를 VEL_HIGH로
                # 아닐 경우 VEL_LOW로 설정
                candidates = []  # candidates 초기화
                print('velocity to', velocity)

        control_hamster(width//2, left_x, right_x)
        cam.show(output)
        if cam.check_key(10) == 'esc': break

hamster.stop()
wait(500)
```

### 교재 원문 관련 유의점

- 283p 트랙 그림에는 30 표지판이 아래쪽(트랙 시작 부근), 70 표지판이 위쪽에 있다. 실제 인식 판정은 `red_y > height // 2`(화면 아래쪽 절반에 빨간 표지판이 보일 때)로 이루어지므로, 표지판을 카메라가 잘 인식할 수 있는 위치에 배치해야 한다.
- `candidates` 리스트는 슬라이드 원문에서 최초 선언 시 `Candidates = []`(대문자 C)로 되어 있으나 이후 전부 `candidates`(소문자)로 사용되고 있다. 원문 오탈자로 보이며, 실행 시에는 처음부터 `candidates = []`로 통일해야 한다.
