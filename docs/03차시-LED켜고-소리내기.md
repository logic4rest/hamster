# 3차시 — LED켜고 소리내기

> 출처: [파이썬으로 배우는 햄스터와 인공지능 (ver240619)](파이썬으로-배우는-햄스터와-인공지능_ver240619.pdf) PDF 55–61쪽

햄스터의 LED를 켜고 끄면서 바퀴를 움직이는 법과, 버저·정확한 음정으로 소리를 내는 법을 배운다.

---

## 01 햄스터 버전에 따른 LED 설정 (필독) (56p)

햄스터 로봇의 LED는 아래 표의 7가지 색상을 표현한다. `leds()` 메소드로 색을 지정하며, LED를 끄려면 `Hamster.LED_OFF` 또는 `0`을 입력한다.

| LED 색상 | 숫자 | 설명 |
|---|---|---|
| `Hamster.LED_OFF` | 0 | LED를 끈다 |
| `Hamster.LED_BLUE` | 1 | LED를 파란색으로 켠다 (R:0, G:0, B:255) |
| `Hamster.LED_GREEN` | 2 | LED를 초록색으로 켠다 (R:0, G:255, B:0) |
| `Hamster.LED_CYAN` | 3 | LED를 하늘색으로 켠다 (R:0, G:255, B:255) |
| `Hamster.LED_RED` | 4 | LED를 빨간색으로 켠다 (R:255, G:0, B:0) |
| `Hamster.LED_MAGENTA` | 5 | LED를 보라색으로 켠다 (R:255, G:0, B:255) |
| `Hamster.LED_YELLOW` | 6 | LED를 노란색으로 켠다 (R:255, G:255, B:0) |
| `Hamster.LED_WHITE` | 7 | LED를 하얀색으로 켠다 (R:255, G:255, B:255) |

**햄스터(기본형) 예시**
```python
hamster = Hamster()  # 기본 햄스터 버전 이용

hamster.leds(hamster.LED_BLUE)  # 양쪽 LED를 파란색으로 설정한다.
hamster.leds(1)  # 양쪽 LED를 파란색으로 설정한다.
```

**햄스터S 예시** — 햄스터S는 풀 컬러 LED를 사용하므로 R, G, B을 직접 입력해 더욱 다양한 색을 표현할 수 있다. `LED_BLUE` 대신 `COLOR_NAME_BLUE`를 사용한다. LED를 끄려면 `HamsterS.COLOR_NAME_OFF` 또는 `0`을 입력한다.
```python
hamster = HamsterS()  # 햄스터 S 버전 이용

hamster.leds(hamster.COLOR_NAME_BLUE)  # 양쪽 LED를 파란색으로 설정한다.
hamster.leds("blue")  # 양쪽 LED를 파란색으로 설정한다.
hamster.leds(0, 0, 255, 0, 0, 255)  # 양쪽 LED를 파란색으로 설정한다
hamster.leds("blue", "off")  # 왼쪽 LED만 파란색으로 켜고, 오른쪽은 끈다.
hamster.leds("blue", "green")  # 왼쪽 LED 파란색, 오른쪽 LED 초록색으로 설정
```

---

## 01 LED켜고 앞으로 이동하기 (57p)

**햄스터(기본형)** — 양쪽 LED를 파란색으로 켜고 앞으로 이동
```python
from roboid import *

hamster = Hamster()

hamster.leds(hamster.LED_BLUE, hamster.LED_BLUE)  # 양쪽 LED를 파란색으로 설정한다.
hamster.wheels(30, 30)  # 왼쪽 바퀴와 오른쪽 바퀴의 속도를 30으로 설정한다.
wait(100)
```

**햄스터S** — 양쪽 LED를 파란색으로 켜고 앞으로 이동
```python
hamster = HamsterS()

hamster.leds(hamster.COLOR_NAME_BLUE, hamster.COLOR_NAME_BLUE)  # 양쪽 LED를 파란색으로 설정한다.
hamster.wheels(30, 30)  # 왼쪽 바퀴와 오른쪽 바퀴의 속도를 30으로 설정한다.
wait(100)
```

색상을 하나만 입력하면 양쪽 LED를 같은 색상으로 설정한다.
```python
hamster.leds(hamster.LED_BLUE)  # 양쪽 LED를 파란색으로 설정한다.
wait(100)
```

양쪽 LED를 다양한 색상으로 켜고 앞으로 이동하게 해본다.

---

## 02 LED 켜고 제자리 돌기 (58p)

회전하는 방향으로 한쪽 LED만 초록색으로 켜고 제자리에서 돌게 한다.

```python
from roboid import *

hamster = Hamster()

hamster.leds(hamster.LED_GREEN, hamster.LED_OFF)  # 왼쪽 LED를 초록색으로 켜고 오른쪽 LED를 끈다.
hamster.wheels(-30, 30)  # 제자리에서 왼쪽으로 돈다.
wait(100)
```

햄스터는 색상에 해당하는 숫자를 입력해도 된다.
```python
hamster.leds(3, 0)  # 왼쪽 LED를 하늘색으로 설정한다.
```

왼쪽 LED 또는 오른쪽 LED, 하나의 값만 설정하려면 `left_led()` 또는 `right_led()` 메소드를 사용해도 된다.
```python
hamster.left_led(hamster.LED_CYAN)  # 왼쪽 LED를 하늘색으로 설정한다.
hamster.leds(-30, 30)  # 제자리에서 왼쪽으로 돈다.
wait(100)
```

---

## 03 소리 내며 뒤로 이동하기 (59p)

버저 소리의 음 높이를 주파수[Hz]로 입력한다.

```python
from roboid import *

hamster = HamsterS()

while True:
    hamster.buzzer(1000)  # 버저 소리의 음 높이를 1000 Hz로 설정한다.
    hamster.wheels(-30)  # 뒤로 이동한다.
    wait(1000)
```

버저 소리의 음 높이는 소수점 둘째 자리까지 입력할 수 있으며, 버저 소리를 끄기 위해서는 0을 입력하면 된다.
```python
hamster.buzzer(261.63)  # 버저 소리의 음 높이를 261.63 Hz로 설정한다.
hamster.wheels(-30)  # 뒤로 이동한다.
```

---

## 04 청력 테스트 (60p)

햄스터 로봇의 버저 소리는 0 ~ 167772.15 Hz까지 입력할 수 있는데, 나이에 따라 사람이 들을 수 있는 최고 음의 높이가 다르다. 버저 소리의 음 높이를 다양하게 변경하면서 얼마나 높은 주파수의 음까지 들을 수 있는지 측정해본다.

```python
from roboid import *

hamster = HamsterS()

hz = 0

while True:
    for _ in range(10):
        hamster.buzzer(hz)
        hz += 500  # 버저 소리의 음 높이를 500씩 높여준다.
        wait(200)
    hz = 0
```

1000 ~ 5000 사이의 값을 넣어보며 확인해본다. 숫자를 매번 직접 넣지 않고 위 코드처럼 반복문을 통해 확인할 수도 있다.

---

## 05 정확한 음정 내기 (61p)

`buzzer()` 메소드는 연속적인 주파수의 음을 낼 수 있지만 소수점 둘째 자리까지밖에 입력할 수 없다는 한계가 있다. `note()` 메소드를 사용하면 오차 0.01% 이하의 정확한 음정을 낼 수 있다. 소리를 끄기 위해서는 `Hamster.NOTE_OFF` 또는 `0`을 입력하면 된다.

```python
from roboid import *

hamster = HamsterS()

hamster.note(hamster.NOTE_C_4)  # 4옥타브 도 음을 소리낸다.
```

4옥타브 도 음에 해당하는 숫자를 입력해도 된다.
```python
hamster.note(40)  # 4옥타브 도 음을 소리낸다.
```

**"무엇이 똑같을까" 노래 만들기**
```python
def play_music():
    for _ in range(2):
        hamster.note("C4", 0.5)
        hamster.note("E4", 0.5)
        hamster.note("G4", 0.5)
    for _ in range(3):
        hamster.note("A4", 0.5)
    hamster.note("G4", 1)
    hamster.note(0, 0.5)

play_music()
```
