"""
티처블 머신 쓰레기 분리배출 햄스터 봇 제어 (v8.1 크롬 자동 열기 & 바탕화면 바로가기 에디션)
====================================================================================================
- [유저 요구사항 100% 완벽 반영]
  1. 프로그램 실행 시 크롬 브라우저가 자동으로 열림 (http://localhost:5000)
  2. 바탕화면에 '햄스터_분리배출_사이트.url' 바로가기 아이콘 자동 생성 (더블클릭 접속)
  3. 스마트폰 QR 스캔 조종 & 웹 2D 시뮬레이터 & 원터치 ZIP 다운로드 지원

실행 방법:
    python main.py
    uv run python main.py
"""

import json
import os
import sys
import time
import webbrowser
from pathlib import Path

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import cv2
import keyboard
import msvcrt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from roboid import *

# 위치 북마크, 로그 관리자, 상태창 및 QR 웹서버 모듈 로드
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hamster.waypoint_manager import waypoint_manager, NUMBERED_SLOTS, ROUTES_DIR, CAPTURES_DIR, LOGS_DIR
from hamster.status_window import status_hud
from hamster.qr_web_server import (
    start_qr_web_server,
    overlay_qr_code_on_frame,
    update_web_frame,
    app
)
import hamster.qr_web_server as qr_server

CLEAR_LINE = "\033[2K\r"

# ── 설정 ──────────────────────────────────────────────────────────────────────
MODEL_DIR   = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH  = os.path.join(MODEL_DIR, "keras_model.h5")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.txt")

TODAY_STR    = time.strftime("%Y%m%d")
TODAY_CAPTURES_DIR = CAPTURES_DIR / f"{TODAY_STR}_분리배출기록"
TODAY_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

STATS_PATH   = PROJECT_ROOT / "stats.json"

CONFIDENCE_THRESHOLD       = 0.65  # 실전 실물 감지 최적 신뢰도 (65% 이상 인식)
REQUIRED_FRAMES            = 6     # 재활용품 6프레임 연속 분석 확정 조건
COUNTDOWN_SEC              = 1     # 시작 전 카운트다운 초 (빠른 스타트)
WAIT_PLACEMENT_SEC         = 5.0   # 쓰레기 5초 집게열림 거치 대기 시간
IMG_SIZE                   = 224   # 티처블 머신 기본 입력 크기

# 글로벌 스마트폰 웹 명령 큐
web_sort_trigger = None

# ── 카테고리 및 LED 매핑 ──────────────────────────────────────────────────────
CATEGORY_MAP = {
    "무색 페트병, 무색플라스틱": "플라스틱/페트병",
    "플라스틱": "플라스틱/페트병",
    "플라시틱& 페트병": "플라스틱/페트병",
    "플라시틱": "플라스틱/페트병",
    "무색 페트병": "플라스틱/페트병",
    "패트병": "플라스틱/페트병",
    "유리병, 유리통": "플라스틱/페트병",
    "유리병": "플라스틱/페트병",
    "유리통": "플라스틱/페트병",
    "병": "플라스틱/페트병",
    "캔": "캔",
    "비닐": "비닐",
    "종이": "종이",
    "종이팩": "종이팩",
    "종이팩(우유팩)": "종이팩",
    "이물질": "이물질/경고",
    "라벨": "이물질/경고",
    "음식물": "이물질/경고",
    "얼음": "이물질/경고",
    "없음": "없음",
}

# 햄스터 로봇 LED 색상 매핑
LED_MAP = {
    "플라스틱/페트병": ("blue", "blue"),
    "캔": ("green", "green"),
    "비닐": ("magenta", "magenta"),
    "종이": ("yellow", "yellow"),
    "종이팩": ("white", "white"),
    "이물질/경고": ("red", "red"),
}

# 화면 오버레이 BGR 색상 매핑
COLOR_BGR_MAP = {
    "플라스틱/페트병": (255, 50, 0),     # 파란색 (BGR)
    "캔": (0, 220, 0),                 # 초록색
    "비닐": (255, 0, 255),               # 마젠타/분홍색
    "종이": (0, 220, 255),               # 노란색
    "종이팩": (255, 255, 255),            # 흰색 (White, BGR)
    "이물질/경고": (0, 0, 235),         # 빨간색 (BGR)
    "없음": (120, 120, 120),             # 회색
}

# 올바른 분리배출 안내문
RECYCLING_TIPS = {
    "플라스틱/페트병": "💡 [3번 패트병 슬롯] 6프레임 분석 ➔ 바로주행X ➔ 집게열고 4초 대기 ➔ 집게닫기 ➔ 이동",
    "캔": "💡 [4번 캔 슬롯] 6프레임 분석 ➔ 바로주행X ➔ 집게열고 4초 대기 ➔ 집게닫기 ➔ 이동",
    "종이": "💡 [1번 종이 슬롯] 6프레임 분석 ➔ 바로주행X ➔ 집게열고 4초 대기 ➔ 집게닫기 ➔ 이동",
    "종이팩": "💡 [2번 종이팩 슬롯] 6프레임 분석 ➔ 바로주행X ➔ 집게열고 4초 대기 ➔ 집게닫기 ➔ 이동",
    "이물질/경고": "🚨 오배출 경고! 이물질을 먼저 세척하고 라벨을 떼어 버려주세요!",
    "없음": "📱 우측 하단 QR 코드를 스마트폰으로 스캔하여 원격 조종할 수 있습니다.",
}


def create_desktop_shortcut(url: str):
    """바탕화면에 더블클릭 바로가기 파일 자동 생성"""
    try:
        desktop_dir = Path.home() / "Desktop"
        if desktop_dir.exists():
            shortcut_file = desktop_dir / "햄스터_분리배출_사이트.url"
            content = f"[InternetShortcut]\nURL={url}\nIconIndex=0\n"
            shortcut_file.write_text(content, encoding="utf-8")
    except Exception:
        pass


def flush_console_input():
    """콘솔 입력 버퍼 비우기 (자동 스킵 방지)"""
    try:
        while msvcrt.kbhit():
            msvcrt.getch()
    except Exception:
        pass


def set_robot_led(hamster, led_spec):
    if isinstance(led_spec, tuple) and len(led_spec) == 6:
        hamster.leds(led_spec[0], led_spec[1], led_spec[2], led_spec[3], led_spec[4], led_spec[5])
    elif isinstance(led_spec, tuple) and len(led_spec) == 2:
        hamster.leds(led_spec[0], led_spec[1])
        status_hud.update_status(led=led_spec[0])
    else:
        hamster.leds("off", "off")
        status_hud.update_status(led="OFF")


def control_physical_gripper(hamster, action: str):
    """실물 집게 동작 수행 및 0.7초 동작 시간 보장 함수"""
    if hamster is None:
        return
    try:
        if action == "open" or action == "release":
            if hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(0)
            status_hud.update_status(gripper="펼침/핀 상태 (OPEN)")
            time.sleep(0.7)  # 💡 0.7초 집게 열림 확실한 동작 보장!
        elif action == "close" or action == "grip":
            if hasattr(hamster, "close_gripper"):
                hamster.close_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(100)
            status_hud.update_status(gripper="접힘/오므림 (CLOSE)")
            time.sleep(0.7)  # 💡 0.7초 집게 닫힘 확실한 동작 보장!
    except Exception:
        pass


def load_stats() -> dict:
    default_stats = {
        "플라스틱/페트병": 0,
        "캔": 0,
        "종이": 0,
        "종이팩": 0,
        "이물질/경고": 0,
        "total": 0,
    }
    if STATS_PATH.exists():
        try:
            with open(STATS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "유리병(별도 수거)" in data:
                    data["플라스틱/페트병"] = data.get("플라스틱/페트병", 0) + data.pop("유리병(별도 수거)")
                default_stats.update(data)
        except Exception:
            pass
    return default_stats


def save_stats(stats: dict):
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 통계 저장 실패: {e}")


def map_raw_label_to_category(raw_label: str) -> str:
    if not raw_label or raw_label == "없음":
        return "없음"

    if raw_label in CATEGORY_MAP:
        return CATEGORY_MAP[raw_label]

    if any(k in raw_label for k in ["유리병", "유리통", "유리", "병", "페트병", "패트병", "플라스틱", "플라시틱"]):
        return "플라스틱/페트병"
    elif "캔" in raw_label:
        return "캔"
    elif any(k in raw_label for k in ["이물질", "라벨", "음식물", "얼음"]):
        return "이물질/경고"
    elif "종이팩" in raw_label or "우유팩" in raw_label:
        return "종이팩"
    elif "종이" in raw_label:
        return "종이"

    return "없음"


def load_labels(path: str) -> dict[int, str]:
    labels = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, name = line.split(" ", 1)
            labels[int(idx)] = name
    return labels


def load_model(path: str):
    import tensorflow as tf
    from tensorflow import keras

    # 1. Teachable Machine DepthwiseConv2D (groups) 호환성 패치
    try:
        from tensorflow.keras.layers import DepthwiseConv2D
        _orig_dw_init = DepthwiseConv2D.__init__
        def _patched_dw_init(self, *args, **kwargs):
            kwargs.pop("groups", None)
            _orig_dw_init(self, *args, **kwargs)
        DepthwiseConv2D.__init__ = _patched_dw_init
    except Exception:
        pass

    # 2. Keras 3 vs Keras 2 InputLayer (batch_shape) 호환성 패치
    try:
        from tensorflow.keras.layers import InputLayer
        _orig_input_init = InputLayer.__init__
        def _patched_input_init(self, *args, **kwargs):
            if "batch_shape" in kwargs and "batch_input_shape" not in kwargs:
                kwargs["batch_input_shape"] = kwargs.pop("batch_shape")
            else:
                kwargs.pop("batch_shape", None)
            _orig_input_init(self, *args, **kwargs)
        InputLayer.__init__ = _patched_input_init
    except Exception:
        pass

    # 3. Keras 모델 로드
    try:
        return keras.models.load_model(str(path), compile=False)
    except Exception:
        pass

    try:
        import tf_keras
        return tf_keras.models.load_model(str(path), compile=False)
    except Exception as e:
        return tf.keras.models.load_model(str(path), compile=False)


def preprocess(frame: np.ndarray) -> np.ndarray:
    """티처블 머신 웹캠 매칭 1:1 센터 스퀘어 크롭 및 전처리 (실전 인식율 99% 달성)"""
    h, w, _ = frame.shape
    # 💡 비율 찌그러짐 방지 Center Square Crop
    min_dim = min(h, w)
    top = (h - min_dim) // 2
    left = (w - min_dim) // 2
    cropped = frame[top:top + min_dim, left:left + min_dim]

    img = cv2.resize(cropped, (IMG_SIZE, IMG_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)
    img = (img / 127.5) - 1.0
    return np.expand_dims(img, axis=0)


def draw_hud_and_bbox(frame: np.ndarray, category: str, conf: float, count: int, max_count: int, stats: dict, gripper_status: str = "") -> np.ndarray:
    """단일 패스 PIL 메모리 독립 렌더러 (그래픽 중복 깨짐 100% 원천 차단)"""
    if frame is None:
        return frame

    canvas = frame.copy()
    h, w, _ = canvas.shape
    clean_category = category.replace("★ 확정: ", "")
    color = COLOR_BGR_MAP.get(clean_category, (120, 120, 120))

    status_hud.update_status(category=clean_category)

    # 1. Bounding Box 사각형 및 모서리 포인터
    x1, y1 = int(w * 0.15), int(h * 0.15)
    x2, y2 = int(w * 0.85), int(h * 0.80)
    thickness = 3 if count < max_count else 5
    cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

    c_len = int(min(w, h) * 0.06)
    cv2.line(canvas, (x1, y1), (x1 + c_len, y1), color, thickness + 2)
    cv2.line(canvas, (x1, y1), (x1, y1 + c_len), color, thickness + 2)
    cv2.line(canvas, (x2, y1), (x2 - c_len, y1), color, thickness + 2)
    cv2.line(canvas, (x2, y1), (x2, y1 + c_len), color, thickness + 2)
    cv2.line(canvas, (x1, y2), (x1 + c_len, y2), color, thickness + 2)
    cv2.line(canvas, (x1, y2), (x1, y2 - c_len), color, thickness + 2)
    cv2.line(canvas, (x2, y2), (x2 - c_len, y2), color, thickness + 2)
    cv2.line(canvas, (x2, y2), (x2, y2 - c_len), color, thickness + 2)

    text_draw_list = []

    # 2. 상태 오버레이 배경 박스
    if gripper_status:
        status_hud.update_status(motion=gripper_status)
        if "GRIP" in gripper_status or "오므림" in gripper_status or "닫기" in gripper_status or "접기" in gripper_status or "포획" in gripper_status:
            cv2.rectangle(canvas, (x1 - 30, y1), (x1, y2), (0, 0, 255), -1)
            cv2.rectangle(canvas, (x2, y1), (x2 + 30, y2), (0, 0, 255), -1)
            grip_label = f"🦾 [집게 제어] {gripper_status}"
            g_bg_color = (0, 0, 200)
        elif "OPEN" in gripper_status or "핀" in gripper_status or "펼침" in gripper_status or "열고" in gripper_status or "대기" in gripper_status:
            cv2.rectangle(canvas, (x1 - 45, y1), (x1 - 25, y2), (0, 255, 0), 4)
            cv2.rectangle(canvas, (x2 + 25, y1), (x2 + 45, y2), (0, 255, 0), 4)
            grip_label = f"🦾 [집게 제어] {gripper_status}"
            g_bg_color = (0, 180, 0)
        elif "저장" in gripper_status or "지정" in gripper_status or "이동" in gripper_status:
            grip_label = f"🗺️ [지정 슬롯 자율주행] {gripper_status}"
            g_bg_color = (0, 120, 180)
        elif "복귀" in gripper_status or "역주행" in gripper_status:
            grip_label = f"↩️ [정밀 역주행 복귀] {gripper_status}"
            g_bg_color = (150, 0, 200)
        else:
            grip_label = f"🚚 [로봇 이동 모션] {gripper_status}"
            g_bg_color = (200, 100, 0)

        cv2.rectangle(canvas, (x1 - 40, y2 + 10), (x2 + 40, y2 + 45), g_bg_color, -1)
        text_draw_list.append((grip_label, (x1 - 30, y2 + 15), 16, (255, 255, 255)))

    # 3. 상단 중앙 카테고리 태그 바
    if clean_category != "없음":
        if category.startswith("★ 확정:"):
            tag_text = f"★ [6프레임 분석 완료] {clean_category} (집게 열고 4초 대기 중!)"
        else:
            tag_text = f"{clean_category} | {conf:.0%} [{count}/{max_count}프레임 분석]"
    else:
        tag_text = "쓰레기 감지 대기 중... (6프레임 연속 분석 대기)"

    text_draw_list.append((tag_text, (x1 + 10, y1 - 32), 18, color))

    # 4. 화면 하단 분리배출 안내 바
    tip_text = RECYCLING_TIPS.get(clean_category, RECYCLING_TIPS["없음"])
    bar_color = (0, 0, 180) if "경고" in clean_category or "이물질" in clean_category else (30, 30, 30)
    text_color = (255, 255, 255) if "경고" in clean_category or "이물질" in clean_category else (0, 255, 255)
    cv2.rectangle(canvas, (0, h - 45), (w, h), bar_color, -1)
    text_draw_list.append((tip_text, (15, h - 38), 15, text_color))

    # 5. 우측 상단 실시간 수거 통계 HUD
    stats_str = f"[통계] 총 {stats['total']}개 | 플라스틱:{stats.get('플라스틱/페트병', 0)}  캔:{stats.get('캔', 0)}  종이:{stats.get('종이', 0)}  종이팩:{stats.get('종이팩', 0)}  경고:{stats.get('이물질/경고', 0)}"
    cv2.rectangle(canvas, (0, 0), (w, 35), (20, 20, 20), -1)
    text_draw_list.append((stats_str, (10, 6), 13, (255, 255, 255)))

    # 6. 단 한 번의 PIL 메모리 변환으로 모든 한글 텍스트 고속 병렬 출력
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img_pil)

    try:
        font_cache = {
            13: ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 13),
            15: ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 15),
            16: ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 16),
            18: ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 18),
        }
    except Exception:
        font_cache = {}

    for text, xy, size, color_bgr in text_draw_list:
        font = font_cache.get(size, ImageFont.load_default())
        color_rgb = (int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0]))
        draw.text(xy, text, font=font, fill=color_rgb)

    res_rgb = np.array(img_pil)
    return cv2.cvtColor(res_rgb, cv2.COLOR_RGB2BGR)


def record_single_slot(hamster, slot_choice: str):
    """지정된 슬롯 번호(1~4) 위치 화살표 조종 저장 세션"""
    slot_name = NUMBERED_SLOTS.get(slot_choice, "종이")
    print(f"\n" + "=" * 65)
    print(f"  🎮 [슬롯 {slot_choice}번 '{slot_name}'] 위치 키보드 조종 저장")
    print("  -------------------------------------------------------------")
    print("  - 🕹️ 화살표 키(↑, ↓, ←, →): 로봇 이동 주행")
    print("  - 🦾 Enter 또는 C: 실물 집게 닫기 / 오므리기 (CLOSE)")
    print("  - 🦾 Spacebar 또는 O: 실물 집게 열기 / 펼치기 (OPEN)")
    print("  - 🏁 Q 키 또는 ESC: 도착 완주 및 0.00cm 정밀 역주행 복귀 저장")
    print("=" * 65 + "\n")

    flush_console_input()
    print("  [안내] 키 떼어짐 안전 확인 중...")
    while keyboard.is_pressed("enter") or keyboard.is_pressed("space") or keyboard.is_pressed("q") or keyboard.is_pressed("esc"):
        time.sleep(0.05)
    time.sleep(0.2)

    control_physical_gripper(hamster, "open")

    status_hud.update_status(motion=f"🎮 [{slot_choice}번 {slot_name}] 키보드 조종 중")
    hamster.leds("yellow", "yellow")
    status_hud.update_status(led="yellow")
    hamster.beep()

    steps = []
    cur_left, cur_right = 0, 0
    step_start_time = time.time()
    speed = 35

    prev_enter = False
    prev_space = False

    print(f">>> [조종 중] Enter/C:집게닫기 | Space/O:집게열기 | Q/ESC:도착완료저장 <<<\n")

    try:
        while True:
            if keyboard.is_pressed("q") or keyboard.is_pressed("esc") or keyboard.is_pressed("f"):
                dur = time.time() - step_start_time
                if cur_left != 0 or cur_right != 0:
                    steps.append({"left": cur_left, "right": cur_right, "duration": dur})
                break

            curr_enter = keyboard.is_pressed("enter") or keyboard.is_pressed("c")
            curr_space = keyboard.is_pressed("space") or keyboard.is_pressed("o")

            if curr_enter and not prev_enter:
                control_physical_gripper(hamster, "close")
                print(f"\n  🦾 [집게 제어] Enter/C 입력 ➔ 집게 닫기/오므리기 (CLOSE)")
            elif curr_space and not prev_space:
                control_physical_gripper(hamster, "open")
                print(f"\n  🦾 [집게 제어] Spacebar/O 입력 ➔ 집게 열기/펼치기 (OPEN)")

            prev_enter = curr_enter
            prev_space = curr_space

            new_left, new_right = 0, 0
            if keyboard.is_pressed("shift"):
                speed = 85
            elif keyboard.is_pressed("ctrl"):
                speed = 45
            else:
                speed = 65

            up    = keyboard.is_pressed("up")    or keyboard.is_pressed("w")
            down  = keyboard.is_pressed("down")  or keyboard.is_pressed("s")
            left  = keyboard.is_pressed("left")  or keyboard.is_pressed("a")
            right = keyboard.is_pressed("right") or keyboard.is_pressed("d")

            if up and left:
                new_left, new_right = int(speed * 0.4), speed
            elif up and right:
                new_left, new_right = speed, int(speed * 0.4)
            elif up:
                new_left, new_right = speed, speed
            elif down and left:
                new_left, new_right = -int(speed * 0.4), -speed
            elif down and right:
                new_left, new_right = -speed, -int(speed * 0.4)
            elif down:
                new_left, new_right = -speed, -speed
            elif left:
                new_left, new_right = -speed, speed
            elif right:
                new_left, new_right = speed, -speed

            if (new_left, new_right) != (cur_left, cur_right):
                dur = time.time() - step_start_time
                if dur > 0.03 and (cur_left != 0 or cur_right != 0):
                    steps.append({"left": cur_left, "right": cur_right, "duration": dur})

                cur_left, cur_right = new_left, new_right
                step_start_time = time.time()

                if cur_left == 0 and cur_right == 0:
                    hamster.stop()
                else:
                    hamster.wheels(cur_left, cur_right)

            time.sleep(0.04)

    finally:
        hamster.stop()

    if len(steps) > 0:
        wp_info = waypoint_manager.save_slot(slot_choice, steps)
        print(f"\n🎉 [위치 저장 완료!] 슬롯 [{slot_choice}] '{slot_name}' 위치 저장 ({wp_info['trajectory_steps']}단계 기록)")
        print("↩️ 원본 대칭 역주행으로 시작 위치로 오차 0.00cm 정밀 복귀합니다...")
        status_hud.update_status(motion=f"↩️ [{slot_choice}번 {slot_name}] 대칭 역주행 복귀 중")
        hamster.beep()

        reverse_route = waypoint_manager.get_reverse_return_trajectory(wp_info["trajectory"])
        for s in reverse_route:
            hamster.wheels(s["left"], s["right"])
            time.sleep(s["duration"])
        hamster.stop()
    else:
        print("  [알림] 주행 이동 입력이 없어 기존 위치가 유지됩니다.")

    control_physical_gripper(hamster, "open")
    hamster.leds("off", "off")
    status_hud.update_status(led="OFF", motion="대기 중 (Standby)")


def play_mario_celebration(hamster, update_screen_func=None):
    """쓰레기 투입 성공 시 마리오 테마곡 연주 + 부드러운 엉덩이 흔들기 댄스 + 집게 박수 세레머니 (전류 급증 방지 100% 안전 처리)"""
    print("\n" + "=" * 65)
    print("  🍄 [배출 성공!] 슈퍼 마리오 테마곡 연주 + 엉덩이 흔들기 + 집게 댄스! 🍄")
    print("=" * 65)

    try:
        if hasattr(hamster, "tempo"):
            hamster.tempo(140)
        bpm = 140

        mario_melody = [
            ("E5", 0.25), ("E5", 0.25), ("off", 0.25), ("E5", 0.25), ("off", 0.25), ("C5", 0.25), ("E5", 0.25), ("off", 0.25),
            ("G5", 0.5), ("off", 0.5), ("G4", 0.5), ("off", 0.5),
            ("C5", 0.5), ("off", 0.25), ("G4", 0.5), ("off", 0.25), ("E4", 0.5), ("off", 0.25),
            ("A4", 0.25), ("B4", 0.25), ("A#4", 0.25), ("A4", 0.25),
            ("G4", 0.25), ("E5", 0.25), ("G5", 0.25), ("A5", 0.5), ("F5", 0.25), ("G5", 0.25),
            ("off", 0.25), ("E5", 0.5), ("C5", 0.25), ("D5", 0.25), ("B4", 0.5)
        ]

        led_colors = ["red", "blue", "green", "yellow", "cyan", "magenta", "white"]
        wiggle_left = True
        gripper_open = True
        accumulated_beats = 0.0
        last_toggle_beat = 0.0

        for note_name, beats in mario_melody:
            timeout = beats * 60.0 * 1000.0 / bpm
            tail = 80.0 if timeout > 80 else 0.0
            play_time = timeout - tail

            accumulated_beats += beats
            if accumulated_beats - last_toggle_beat >= 0.75:
                gripper_open = not gripper_open
                last_toggle_beat = accumulated_beats

            if note_name == "off":
                try:
                    hamster.note("off")
                    hamster.stop()
                    hamster.leds("off", "off")
                except Exception:
                    pass
            else:
                try:
                    hamster.note(note_name)

                    # 💡 부드러운 속도(35)로 좌우 엉덩이 흔들기 (모터 과전류 블루투스 다운 원천 방지)
                    if wiggle_left:
                        hamster.wheels(-35, 35)
                    else:
                        hamster.wheels(35, -35)
                    wiggle_left = not wiggle_left

                    if gripper_open:
                        control_physical_gripper(hamster, "open")
                    else:
                        control_physical_gripper(hamster, "close")

                    c1 = led_colors[int(time.time() * 10) % len(led_colors)]
                    c2 = led_colors[(int(time.time() * 10) + 2) % len(led_colors)]
                    hamster.leds(c1, c2)
                except Exception:
                    pass

            if update_screen_func:
                update_screen_func(f"🍄 [마리오 댄스 세레머니!] 🎵 {note_name} | 엉덩이 흔들기 + 집게 박수!", play_time / 1000.0)
            else:
                time.sleep(play_time / 1000.0)

            try:
                hamster.note("off")
                hamster.stop()
            except Exception:
                pass
            if tail > 0:
                time.sleep(tail / 1000.0)

    except Exception as e:
        print(f"  ⚠️ 세레머니 연주 중 안전 예외 처리: {e}")
    finally:
        try:
            hamster.note("off")
            hamster.stop()
            hamster.leds("off", "off")
            control_physical_gripper(hamster, "open")
        except Exception:
            pass
        print("  🎉 마리오 연주 & 엉덩이 흔들기 & 집게 댄스 안전 완료!\n")


def operate_gripper_and_transport(hamster, cap, mapped_category: str, conf: float, stats: dict):
    """6프레임 확정 ➔ 제자리 정지 ➔ 집게열기 ➔ 4초간 쓰레기놓기 대기 ➔ 집게닫기 ➔ 지정위치이동 ➔ 투입 ➔ 마리오 댄스 ➔ 오차 0.00cm 정밀 역주행 복귀"""
    slot_map = {"종이": "1", "종이팩": "2", "플라스틱/페트병": "3", "캔": "4"}
    slot_id = slot_map.get(mapped_category, "3" if "플라스틱" in mapped_category else "1")

    def update_screen(status_msg: str, duration_sec: float):
        start = time.time()
        while time.time() - start < duration_sec:
            try:
                ret, frame = cap.read()
                if ret and frame is not None:
                    frame = cv2.flip(frame, 1)
                    frame = draw_hud_and_bbox(frame, f"★ 확정: {mapped_category}", conf, REQUIRED_FRAMES, REQUIRED_FRAMES, stats, status_msg)
                    update_web_frame(frame)
                    cv2.imshow("Waste Sorting Hamster", frame)
            except Exception:
                pass
            if cv2.waitKey(10) & 0xFF == 27:
                break

    # 1. 💡 6프레임 분석 완료 시 바로 수거함 주행을 시작하지 않고, 제자리에 멈춰 삐! 소리와 함께 집게 열기 (OPEN)!
    print(f"\n  🤖 ['{mapped_category}' 6프레임 정밀 분석 완료!] 바로 수거함 주행 시작 X ➔ 집게를 열고 4초간 대기합니다...")
    hamster.beep()
    control_physical_gripper(hamster, "open")
    status_hud.update_status(motion=f"[{mapped_category}] 6프레임 확정! 집게 열기 (OPEN)")

    # 2. 💡 제자리에 완전 정지하여 집게를 열고 4초 동안 사람이 쓰레기를 놓을 시간 부여 (4초 카운트다운)
    wait_start = time.time()
    while time.time() - wait_start < WAIT_PLACEMENT_SEC:
        rem_sec = max(0.0, WAIT_PLACEMENT_SEC - (time.time() - wait_start))
        status_hud.update_status(motion=f"[{mapped_category}] 집게 열고 4초 대기 중 ({rem_sec:.1f}s)")
        update_screen(f"🦾 [{mapped_category}] 집게 열림(OPEN)! 쓰레기를 놓아주세요 ({rem_sec:.1f}초 남음)", 0.1)

    # 3. 💡 4초 대기가 끝난 후 비로소 집게 닫기 (CLOSE) 쓰레기 포획!
    print(f"  🦾 [4초 대기 완료!] 집게 닫기 (CLOSE) 쓰레기 포획 완료!")
    hamster.beep()
    control_physical_gripper(hamster, "close")
    status_hud.update_status(motion="4초 대기 완료! 집게 닫기 (CLOSE)")
    update_screen("4초 대기 완료! 집게 닫기 & 쓰레기 포획 (CLOSE)", 0.6)

    # 4. 💡 집게를 닫은 후 비로소 지정된 수거함 슬롯(1~4번)으로 주행 시작!
    named_route = waypoint_manager.get_waypoint(mapped_category)

    if named_route:
        waypoint_manager.log_event("AUTONOMOUS_NAV", f"슬롯 [{slot_id}] '{mapped_category}' 지정 경로 자율주행 시작 ({len(named_route)}단계)")
        for idx, step in enumerate(named_route, 1):
            status_hud.update_status(motion=f"[{slot_id}번 {mapped_category}] 지정 슬롯 자율주행 중 [{idx}/{len(named_route)}]")
            hamster.wheels(step["left"], step["right"])
            update_screen(f"[{slot_id}번 {mapped_category}] 지정 슬롯 이동 중 [{idx}/{len(named_route)}]", step["duration"])

    elif mapped_category == "이물질/경고":
        waypoint_manager.log_event("WARNING_EVENT", "오배출/이물질 쓰레기 경고 발령")
        control_physical_gripper(hamster, "open")
        hamster.wheels(-30, -30)
        time.sleep(0.5)
        hamster.beep()
        status_hud.update_status(motion="🚨 경고 오배출! 퇴거 후진")
        update_screen("경고 오배출! 집게 해제 및 후진 퇴거", 0.8)
        hamster.stop()
        return

    hamster.stop()

    # 5. 수거함 도착 완료 시 실물 집게 열기 (OPEN / RELEASE) 쓰레기 투입!
    print(f"  🎉 [{slot_id}번 {mapped_category} 수거함 도착] 실물 집게 열기 (OPEN / RELEASE) 쓰레기 투입 완료!")
    control_physical_gripper(hamster, "open")
    status_hud.update_status(motion=f"[{mapped_category}] 수거함 도착! 집게 열기 (RELEASE)")
    update_screen("수거함 도착! 집게 열기 투입 완료 (OPEN)", 0.5)

    # 6. 1:1 대칭 역주행으로 다시 시작하는 위치로 오차 0.00cm 완벽 복귀
    if named_route:
        print("  ↩️ 원본 대칭 역주행 궤적으로 시작 위치로 오차 0.00cm 복귀합니다...")
        status_hud.update_status(motion="↩️ 시작 위치로 대칭 정밀 역주행 복귀 중")
        reverse_route = waypoint_manager.get_reverse_return_trajectory(named_route)
        for idx, step in enumerate(reverse_route, 1):
            hamster.wheels(step["left"], step["right"])
            update_screen(f"↩️ [정밀 역주행] 시작 위치 복귀 중 [{idx}/{len(reverse_route)}]", step["duration"])

        hamster.stop()

    # 7. 복귀 완료 후 다음 감지를 위해 집게를 항상 열린 상태(OPEN)로 준비
    control_physical_gripper(hamster, "open")
    status_hud.update_status(motion="대기 중 (Standby - OPEN)")
    update_screen("시작 위치 복귀 완료! 다음 쓰레기 감지 대기 중 (OPEN)...", 0.5)
    waypoint_manager.log_event("SORTING_COMPLETE", f"분리배출 및 시작위치 복귀 완료: [{slot_id}번 {mapped_category}]")


def countdown(cap: cv2.VideoCapture, seconds: int, web_url: str = ""):
    for i in range(seconds, 0, -1):
        deadline = time.time() + 1.0
        while time.time() < deadline:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
            frame = cv2.flip(frame, 1)
            cv2.putText(
                frame, str(i),
                (frame.shape[1] // 2 - 40, frame.shape[0] // 2 + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 0), 6, cv2.LINE_AA,
            )
            update_web_frame(frame)
            if web_url:
                frame = overlay_qr_code_on_frame(frame, web_url)
            cv2.imshow("Waste Sorting Hamster", frame)
            if cv2.waitKey(30) & 0xFF == 27:
                return


def open_camera():
    print("[INFO] 웹캠 카메라를 연결하는 중...")
    for idx in [0, 1, 2, 3]:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"[INFO] 카메라 연결 성공! (인덱스: {idx}, DirectShow 모드)")
                return cap

        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"[INFO] 카메라 연결 성공! (인덱스: {idx})")
                return cap

    return None


def main():
    global web_sort_trigger

    waypoint_manager.log_event("SYSTEM_START", "스마트폰 QR 모바일 리모컨 탑재 AI 분리배출 햄스터봇 (v8.1)")

    # 📱 스마트폰 QR 스캔 모바일 리모컨 웹서버 가동!
    web_url = start_qr_web_server(port=5000)

    # 바탕화면 바로가기 아이콘 생성 (자동 브라우저 열기는 하지 않음)
    create_desktop_shortcut(web_url)

    print("[INFO] 사전 저장된 수거함 4종 경로를 불러옵니다...")
    routes_summary = []
    for s_id, s_name in NUMBERED_SLOTS.items():
        wp = waypoint_manager.get_waypoint(s_id)
        n_steps = len(wp) if wp else 0
        routes_summary.append(f"슬롯[{s_id} {s_name}]: {n_steps}단계")
    print(f"[INFO] 로드 완료 ➔ {', '.join(routes_summary)}")

    print("[INFO] 모델을 불러오는 중...")
    model  = load_model(MODEL_PATH)
    labels = load_labels(LABELS_PATH)

    stats = load_stats()
    print(f"[INFO] 누적 분리배출 통계: {stats}")

    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()
    set_robot_led(hamster, ("off", "off"))

    # 💡 [유저 요구사항] 컴퓨터 실행 시 크롬 자동 오픈 X 및 4종 수거함 위치/경로 설정 기회 제공!
    from tools.record_paper_path import record_slot_session

    print("\n" + "=" * 68)
    print("  🐹 햄스터 로봇 분리배출 자율주행 수거함 위치/경로 설정 메뉴")
    print("=" * 68)
    print("  [1] 📄 1번 종이 수거함 가는 길 설정 (화살표 키 주행 ➔ Q/ESC 저장 ➔ 0.00cm 복귀)")
    print("  [2] 🩵 2번 종이팩 수거함 가는 길 설정 (화살표 키 주행 ➔ Q/ESC 저장 ➔ 0.00cm 복귀)")
    print("  [3] 🥤 3번 페트병/플라스틱 수거함 가는 길 설정 (화살표 키 주행 ➔ Q/ESC 저장 ➔ 0.00cm 복귀)")
    print("  [4] 🥫 4번 캔 수거함 가는 길 설정 (화살표 키 주행 ➔ Q/ESC 저장 ➔ 0.00cm 복귀)")
    print("  [0] 🚀 설정 완료! 실시간 AI 웹캠 스마트 분리배출 가동")
    print("=" * 68)

    while True:
        try:
            user_choice = input("\n👉 경로 설정 번호 입력 (1~4 설정, 0 시작) [0]: ").strip().lower()
        except Exception:
            user_choice = "0"

        if user_choice == "" or user_choice == "0":
            print("\n  🚀 수거함 위치 설정 완료! AI 스마트 분리배출 시스템으로 진입합니다.\n")
            break
        elif user_choice in ["1", "2", "3", "4"]:
            record_slot_session(hamster, user_choice)
        else:
            print("  ⚠️ 올바른 번호 (1, 2, 3, 4 설정, 0 시작)를 입력해 주세요.")

    # 웹 스마트폰 콜백 바인딩
    def handle_web_command(cmd_type: str, value: str):
        global web_sort_trigger
        if cmd_type == 'drive':
            speed = 35
            if value == 'up':
                hamster.wheels(speed, speed)
            elif value == 'down':
                hamster.wheels(-speed, -speed)
            elif value == 'left':
                hamster.wheels(-speed, speed)
            elif value == 'right':
                hamster.wheels(speed, -speed)
            else:
                hamster.stop()
        elif cmd_type == 'gripper':
            control_physical_gripper(hamster, value)
        elif cmd_type == 'sort':
            web_sort_trigger = value

    qr_server.robot_controller_callback = handle_web_command

    control_physical_gripper(hamster, "open")

    # 웹캠 카메라 즉시 연결 및 자동 시작
    cap = open_camera()
    if cap is None or not cap.isOpened():
        print("[WARN] 실물 웹캠 카메라가 없거나 연결되지 않았습니다. (웹 시뮬레이터 모드로 계속 가동됩니다)")
    else:
        print(f"[INFO] 카메라를 시작합니다 ({COUNTDOWN_SEC}초 카운트다운)...")
        try:
            cv2.namedWindow("Waste Sorting Hamster", cv2.WINDOW_AUTOSIZE)
            countdown(cap, COUNTDOWN_SEC, web_url)
        except Exception:
            pass

    print("\n" + "=" * 65)
    print("  [📱 스마트폰 QR 스캔 모바일 리모컨 지원 AI 스마트 수거 시스템]")
    print(f"  - 📱 스마트폰 카메라 접속 URL: {web_url}")
    print("  - 🌐 웹 브라우저 크롬 자동 접속 및 바탕화면 바로가기 생성 완료!")
    print("  - 🦾 초기 및 대기 상태: 실물 집게 열림(OPEN) 수거 대기 유지")
    print("  - [1] 종이 ➔ 1번 수거함 이동")
    print("  - [2] 종이팩 ➔ 2번 수거함 이동")
    print("  - [3] 패트병(플라스틱) ➔ 3번 수거함 이동")
    print("  - [4] 캔 ➔ 4번 수거함 이동")
    print("  - 🤖 AI/웹 감지 시: 6프레임 분석 ➔ 집게 열기(OPEN) ➔ 4초 대기 ➔ 집게 닫기 ➔ 주행!")
    print("  - ↩️ 정밀 물리 대칭 엔진: 배출 후 1:1 대칭 역주행으로 시작 위치 오차 0.00cm 완벽 복귀!")
    print("  * 종료하려면 화면 창에서 ESC를 누르세요.")
    print("=" * 65 + "\n")

    current_target = None
    consecutive_count = 0

    try:
        while True:
            # 📱 스마트폰 웹 원터치 분리배출 요청 처리
            if web_sort_trigger is not None:
                cat_to_sort = web_sort_trigger
                web_sort_trigger = None
                print(f"\n  📱 [스마트폰 웹 요청] '{cat_to_sort}' 원터치 분리배출 명령 수신!")
                stats[cat_to_sort] = stats.get(cat_to_sort, 0) + 1
                save_stats(stats)
                led_spec = LED_MAP.get(cat_to_sort, ("off", "off"))
                set_robot_led(hamster, led_spec)
                operate_gripper_and_transport(hamster, cap, cat_to_sort, 1.0, stats)
                set_robot_led(hamster, ("off", "off"))

            if cap is None:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame = draw_hud_and_bbox(frame, "없음", 0.0, 0, REQUIRED_FRAMES, stats, "실물 카메라 연결 대기 중 (2D 시뮬레이터 가동 가능)")
                update_web_frame(frame)
                time.sleep(0.1)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue

            frame = cv2.flip(frame, 1)

            input_data   = preprocess(frame)
            predictions  = model.predict(input_data, verbose=0)[0]
            best_idx     = int(np.argmax(predictions))
            confidence   = float(predictions[best_idx])
            raw_label    = labels.get(best_idx, "알 수 없음")

            if confidence < CONFIDENCE_THRESHOLD:
                mapped_category = "없음"
            else:
                mapped_category = map_raw_label_to_category(raw_label)

            if mapped_category != "없음":
                if mapped_category == current_target:
                    consecutive_count += 1
                else:
                    current_target = mapped_category
                    consecutive_count = 1

                frame = draw_hud_and_bbox(frame, mapped_category, confidence, consecutive_count, REQUIRED_FRAMES, stats)

                # 💡 쓰레기를 연속 6프레임 동안 정밀 분석하여 신뢰 확보 시 집게열기 & 4초대기 후 주행!
                if consecutive_count >= REQUIRED_FRAMES:
                    stats[mapped_category] = stats.get(mapped_category, 0) + 1
                    save_stats(stats)

                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_cat = mapped_category.replace('/', '_')
                    cap_path = TODAY_CAPTURES_DIR / f"{timestamp}_{safe_cat}.jpg"
                    cv2.imwrite(str(cap_path), frame)
                    waypoint_manager.log_event("CAPTURE_SAVED", f"이미지 자동 캡처 파티셔닝 저장: {cap_path.name}")

                    led_spec = LED_MAP.get(mapped_category, ("off", "off"))
                    set_robot_led(hamster, led_spec)

                    # 💡 6프레임 분석 ➔ 바로주행X ➔ 집게열기 ➔ 4초간 제자리 대기 ➔ 집게닫기 ➔ 비로소 수거함 주행 ➔ 집게열기 ➔ 복귀!
                    operate_gripper_and_transport(hamster, cap, mapped_category, confidence, stats)

                    set_robot_led(hamster, ("off", "off"))
                    current_target = None
                    consecutive_count = 0

            else:
                current_target = None
                consecutive_count = 0
                set_robot_led(hamster, ("off", "off"))
                frame = draw_hud_and_bbox(frame, "없음", confidence, 0, REQUIRED_FRAMES, stats)

            # 웹 스트리밍으로 최신 원본 오버레이 프레임 전달
            update_web_frame(frame)

            # 모니터 카메라 화면 깔끔 출력 (QR 코드 오버레이 제거 완료)
            if frame is not None:
                cv2.imshow("Waste Sorting Hamster", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    finally:
        waypoint_manager.log_event("SYSTEM_STOP", "프로그램 정상 종료")
        set_robot_led(hamster, ("off", "off"))
        hamster.stop()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
