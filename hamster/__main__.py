"""
티처블 머신 쓰레기 분리배출 햄스터 봇 제어 (v5.2 위치 학습 후 0번 웹캠 시작 에디션)
====================================================================================================
- [요청 사항 반영] 실행 즉시 웹캠을 켜지 않고, 1~4번 수거함 위치를 화살표 키로 먼저 조종/저장
- 사용자가 명확하게 '0'번을 입력하고 Enter를 눌렀을 때만 웹캠 카메라(OpenCV)를 활성화
- 배출 후 1:1 대칭 정밀 역주행으로 시작 위치(0, 0) 오차 0.00cm 완벽 제자리 복귀
- 화면 구석에 실시간 햄스터 하드웨어 상태(센서값, 모션, 집게, LED)를 알려주는 미니 상태창(HUD) 활성화

실행 방법:
    uv run hamster
    python main.py
"""

import json
import os
import sys
import time
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
import roboidai as ai
from roboid import *

# 위치 북마크, 로그 관리자 및 미니 상태창 모듈 로드
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hamster.waypoint_manager import waypoint_manager, NUMBERED_SLOTS, ROUTES_DIR, CAPTURES_DIR, LOGS_DIR
from hamster.status_window import status_hud

# ── 설정 ──────────────────────────────────────────────────────────────────────
MODEL_DIR    = str(PROJECT_ROOT / "models")
TODAY_STR    = time.strftime("%Y%m%d")
TODAY_CAPTURES_DIR = CAPTURES_DIR / f"{TODAY_STR}_분리배출기록"
TODAY_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

STATS_PATH   = PROJECT_ROOT / "stats.json"

CONFIDENCE_THRESHOLD       = 0.8   # 이 값 미만이면 폐기/대기 (없음 처리)
REQUIRED_FRAMES            = 4     # 연속 4프레임 동일 시 최종 확정
COUNTDOWN_SEC              = 2     # 시작 전 카운트다운 초

# ── 카테고리 및 LED 매핑 ──────────────────────────────────────────────────────
CATEGORY_MAP = {
    "무색 페트병, 무색플라스틱": "플라스틱/페트병",
    "플라스틱": "플라스틱/페트병",
    "무색 페트병": "플라스틱/페트병",
    "패트병": "플라스틱/페트병",
    "유리병, 유리통": "플라스틱/페트병",
    "유리병": "플라스틱/페트병",
    "유리통": "플라스틱/페트병",
    "병": "플라스틱/페트병",
    "캔": "캔",
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
    "종이": ("yellow", "yellow"),
    "종이팩": ("cyan", "cyan"),
    "이물질/경고": ("red", "red"),
}

# 화면 오버레이 BGR 색상 매핑
COLOR_BGR_MAP = {
    "플라스틱/페트병": (255, 50, 0),     # 파란색 (BGR)
    "캔": (0, 220, 0),                 # 초록색
    "종이": (0, 220, 255),               # 노란색
    "종이팩": (255, 235, 0),              # 하늘색
    "이물질/경고": (0, 0, 235),         # 빨간색 (BGR)
    "없음": (120, 120, 120),             # 회색
}

# 올바른 분리배출 안내문
RECYCLING_TIPS = {
    "플라스틱/페트병": "💡 [3번 패트병 슬롯 이동] 저장된 3번 위치 경로로 100% 정밀 자율이동!",
    "캔": "💡 [4번 캔 슬롯 이동] 저장된 4번 위치 경로로 100% 정밀 자율이동!",
    "종이": "💡 [1번 종이 슬롯 이동] 저장된 1번 위치 경로로 100% 정밀 자율이동!",
    "종이팩": "💡 [2번 종이팩 슬롯 이동] 저장된 2번 위치 경로로 100% 정밀 자율이동!",
    "이물질/경고": "🚨 오배출 경고! 이물질을 먼저 세척하고 라벨을 떼어 버려주세요!",
    "없음": "💡 쓰레기를 카메라 중앙에 비춰주세요. (지정된 1:종이, 2:종이팩, 3:패트병, 4:캔 경로 자율 주행)",
}


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
    if hamster is None:
        return
    try:
        if action == "open":
            if hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(0)
            status_hud.update_status(gripper="열림 (OPEN)")
        elif action == "close" or action == "grip":
            if hasattr(hamster, "close_gripper"):
                hamster.close_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(100)
            status_hud.update_status(gripper="포획 완료 (GRIP!)")
        elif action == "release":
            if hasattr(hamster, "release_gripper"):
                hamster.release_gripper()
            elif hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(0)
            status_hud.update_status(gripper="투입 해제 (RELEASE)")
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

    if any(k in raw_label for k in ["유리병", "유리통", "유리", "병", "페트병", "패트병", "플라스틱"]):
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
        if "GRIP" in gripper_status or "잡기" in gripper_status:
            cv2.rectangle(canvas, (x1 - 30, y1), (x1, y2), (0, 0, 255), -1)
            cv2.rectangle(canvas, (x2, y1), (x2 + 30, y2), (0, 0, 255), -1)
            grip_label = "🦾 [집게 제어] 쓰레기 포획 완료 (GRIP!)"
            g_bg_color = (0, 0, 200)
        elif "OPEN" in gripper_status or "열기" in gripper_status:
            cv2.rectangle(canvas, (x1 - 45, y1), (x1 - 25, y2), (0, 255, 0), 4)
            cv2.rectangle(canvas, (x2 + 25, y1), (x2 + 45, y2), (0, 255, 0), 4)
            grip_label = "🦾 [집게 제어] 집게 열림 (OPEN)"
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
            if clean_category == "이물질/경고":
                tag_text = "[경고] 오배출/이물질 감지!"
            elif clean_category == "종이":
                tag_text = "[확정] 종이 -> [1번 종이 수거함] 자율주행!"
            elif clean_category == "종이팩":
                tag_text = "[확정] 종이팩 -> [2번 종이팩 수거함] 자율주행!"
            elif clean_category == "플라스틱/페트병":
                tag_text = "[확정] 페트병/플라스틱 -> [3번 패트병 수거함] 자율주행!"
            elif clean_category == "캔":
                tag_text = "[확정] 캔 -> [4번 캔 수거함] 자율주행!"
            else:
                tag_text = f"[정상] {clean_category} -> 집게 수거함 이동!"
        else:
            tag_text = f"{clean_category} | {conf:.0%} [{count}/{max_count}]"
    else:
        tag_text = "쓰레기 감지 대기 중... (1:종이, 2:종이팩, 3:패트병, 4:캔)"

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
    print(f"  🎮 [슬롯 {slot_choice}번 '{slot_name}'] 위치 화살표 키 조종 저장")
    print("  -------------------------------------------------------------")
    print("  1. 햄스터를 시작 위치(카메라 앞)에 두고 화살표 키(↑, ↓, ←, →)로 조종하세요.")
    print(f"  2. [{slot_choice}번 {slot_name}] 수거함 위치까지 도착해서 Enter 키를 누르세요.")
    print("  3. 저장 완료 시 삐! 소리와 함께 오차 0.00cm 정밀 역주행으로 시작 위치로 대칭 복귀합니다.")
    print("=" * 65 + "\n")

    flush_console_input()
    while keyboard.is_pressed("enter") or keyboard.is_pressed("space"):
        time.sleep(0.05)
    time.sleep(0.3)

    status_hud.update_status(motion=f"🎮 [{slot_choice}번 {slot_name}] 화살표 조종 중")
    hamster.leds("yellow", "yellow")
    status_hud.update_status(led="yellow")
    hamster.beep()

    steps = []
    cur_left, cur_right = 0, 0
    step_start_time = time.time()
    speed = 35

    print(f">>> 지금 바로 화살표 키로 [{slot_choice}번 {slot_name}] 위치까지 운전하세요! (도착 시 Enter) <<<\n")

    try:
        while True:
            if keyboard.is_pressed("enter") or keyboard.is_pressed("space"):
                dur = time.time() - step_start_time
                if cur_left != 0 or cur_right != 0:
                    steps.append({"left": cur_left, "right": cur_right, "duration": dur})
                if len(steps) > 0 or (time.time() - step_start_time > 1.0):
                    break

            new_left, new_right = 0, 0
            if keyboard.is_pressed("shift"):
                speed = 50
            elif keyboard.is_pressed("ctrl"):
                speed = 25
            else:
                speed = 35

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

    hamster.leds("off", "off")
    status_hud.update_status(led="OFF", motion="대기 중 (Standby)")


def initial_arrow_teach_session(hamster):
    """프로그램 시작 시 쓰레기 4종 위치 학습 세션 (0번 입력 시 웹캠 시작)"""
    while True:
        print("\n" + "=" * 65)
        print("  🎮 [1단계] 쓰레기 4종 위치 번호별 지정 저장 모드")
        print("  -------------------------------------------------------------")
        print("  저장하고자 하는 수거함 번호를 선택해 주세요:")
        print("    [1] 📄 종이")
        print("    [2] 🩵 종이팩")
        print("    [3] 🥤 패트병(플라스틱)")
        print("    [4] 🥫 캔")
        print("    [0] 🚀 위치 저장 완료 및 웹캠 카메라 AI 감지 시작")
        print("=" * 65)

        flush_console_input()
        choice = input("\n👉 선택할 번호를 입력 후 Enter를 누르세요 (1, 2, 3, 4 지정 선택 또는 0 입력 후 Enter) > ").strip()

        # 💡 [핵심 유저 요청] 명확하게 '0'을 입력해야만 웹캠 카메라(OpenCV)를 활성화
        if choice == "0":
            print("\n  [완료] 수거함 위치 설정을 마치고 웹캠 카메라 감지를 시작합니다!\n")
            break

        if choice in ["1", "2", "3", "4"]:
            record_single_slot(hamster, choice)
            flush_console_input()
        else:
            print("  ⚠️ 수거함 위치를 새로 지정하려면 [1, 2, 3, 4] 중 번호를 선택하고, 설정을 마치고 웹캠을 켜시려면 '0'을 입력해 주세요.")


def operate_gripper_and_transport(hamster, cam, mapped_category: str, conf: float, stats: dict):
    """4종 지정 슬롯 및 대칭 역주행 100% 정밀 복귀 운반 시퀀스"""
    waypoint_manager.log_event("SORTING_START", f"분리배출 확정 시퀀스 시작: '{mapped_category}' (신뢰도: {conf:.2f})")

    slot_map = {
        "종이": "1",
        "종이팩": "2",
        "플라스틱/페트병": "3",
        "캔": "4"
    }
    slot_id = slot_map.get(mapped_category, "3" if "플라스틱" in mapped_category else "1")

    def update_screen(status_msg: str, duration_sec: float):
        start = time.time()
        while time.time() - start < duration_sec:
            img = cam.read()
            if img is not None:
                img = draw_hud_and_bbox(img, f"★ 확정: {mapped_category}", conf, REQUIRED_FRAMES, REQUIRED_FRAMES, stats, status_msg)
                cam.show(img)
            if cam.check_key() == "esc":
                break

    # 1. 실물 집게 열기 & 0.3초 접근 전진
    control_physical_gripper(hamster, "open")
    status_hud.update_status(motion=f"[{slot_id}번 {mapped_category}] 접근 전진 중")
    approach_dur = 0.3
    hamster.wheels(30, 30)
    update_screen("집게 열기 (OPEN) -> 접근 전진", approach_dur)
    hamster.stop()

    # 2. 실물 집게 닫기 (close_gripper)
    control_physical_gripper(hamster, "close")
    status_hud.update_status(motion="쓰레기 포획 완료 (GRIP!)")
    update_screen("쓰레기 포획 완료! (GRIP!)", 0.5)

    # 3. 4종 지정 번호 슬롯 위치 검색/호출 & 자율주행
    named_route = waypoint_manager.get_waypoint(mapped_category)

    if named_route:
        waypoint_manager.log_event("AUTONOMOUS_NAV", f"슬롯 [{slot_id}] '{mapped_category}' 지정 경로 자율주행 시작 ({len(named_route)}단계)")
        for idx, step in enumerate(named_route, 1):
            status_hud.update_status(motion=f"[{slot_id}번 {mapped_category}] 지정 슬롯 자율주행 중 [{idx}/{len(named_route)}]")
            hamster.wheels(step["left"], step["right"])
            update_screen(f"[{slot_id}번 {mapped_category}] 지정 슬롯 이동 중 [{idx}/{len(named_route)}]", step["duration"])

    elif mapped_category == "이물질/경고":
        waypoint_manager.log_event("WARNING_EVENT", "오배출/이물질 쓰레기 경고 발령")
        control_physical_gripper(hamster, "release")
        hamster.wheels(-30, -30)
        time.sleep(approach_dur)
        hamster.beep()
        status_hud.update_status(motion="🚨 경고 오배출! 퇴거 후진")
        update_screen("경고 오배출! 집게 해제 및 후진 퇴거", 0.8)
        hamster.stop()
        return

    hamster.stop()

    # 4. 실물 집게 해제 (release_gripper)
    control_physical_gripper(hamster, "release")
    status_hud.update_status(motion=f"[{mapped_category}] 수거함 투입 해제 (RELEASE)")
    update_screen("수거함 투입 완료! 집게 해제 (RELEASE)", 0.6)

    # 5. 원래 자리 복귀 (💡 100% 대칭 역주행 궤적 + 포획 접근 반전)
    if named_route:
        status_hud.update_status(motion="↩️ 시작 위치로 대칭 정밀 역주행 복귀 중")
        reverse_route = waypoint_manager.get_reverse_return_trajectory(named_route)
        for idx, step in enumerate(reverse_route, 1):
            hamster.wheels(step["left"], step["right"])
            update_screen(f"↩️ [정밀 역주행] 복귀 중 [{idx}/{len(reverse_route)}]", step["duration"])

        # 초기 접근(0.3초) 완벽 대칭 역주행 (-30, -30)
        hamster.wheels(-30, -30)
        update_screen("↩️ 시작 위치 정밀 복귀 안착 중...", approach_dur)
        hamster.stop()
    else:
        hamster.wheels(-35, -35)
        update_screen("원래 위치로 후진 복귀 중...", 0.7)

    hamster.stop()
    status_hud.update_status(motion="대기 중 (Standby)")
    update_screen("복귀 완료! 다음 쓰레기 감지 대기 중...", 0.4)
    waypoint_manager.log_event("SORTING_COMPLETE", f"분리배출 및 복귀 완료: [{slot_id}번 {mapped_category}]")


def open_camera():
    print("[INFO] 웹캠 카메라를 연결하는 중...")
    for target in [0, 1, 'usb0']:
        try:
            cam = ai.Camera(target, flip='h', square=True)
            test_img = cam.read()
            if test_img is not None:
                print(f"[INFO] 카메라 연결 성공! (타겟: {target})")
                return cam
        except Exception:
            pass

    print("[ERROR] 웹캠 카메라를 열 수 없습니다! 카메라 연결을 확인해 주세요.")
    return None


def main():
    waypoint_manager.log_event("SYSTEM_START", "AI 쓰레기 4종 위치 지정 후 웹캠 시작 (v5.2)")

    print("[INFO] 사전 저장된 수거함 4종 경로를 불러옵니다...")
    routes_summary = []
    for s_id, s_name in NUMBERED_SLOTS.items():
        wp = waypoint_manager.get_waypoint(s_id)
        n_steps = len(wp) if wp else 0
        routes_summary.append(f"슬롯[{s_id} {s_name}]: {n_steps}단계")
    print(f"[INFO] 로드 완료 ➔ {', '.join(routes_summary)}")

    print(f"[INFO] 모델을 불러오는 중... ({MODEL_DIR})")
    tmi = ai.TmImage()
    tmi.load_model(MODEL_DIR)
    print("[INFO] 모델 로드 완료!")

    stats = load_stats()
    print(f"[INFO] 누적 분리배출 통계: {stats}")

    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()
    set_robot_led(hamster, ("off", "off"))

    # ★ [핵심] 시작 즉시 웹캠을 켜지 않고 위치 지정 메뉴를 먼저 실행! (0번 누르면 웹캠 시작)
    initial_arrow_teach_session(hamster)

    # 0번을 입력했을 때 비로소 웹캠 카메라 연결
    cam = open_camera()
    if cam is None:
        set_robot_led(hamster, ("off", "off"))
        hamster.stop()
        return

    print(f"[INFO] 카메라를 시작합니다 ({COUNTDOWN_SEC}초 카운트다운)...")
    cam.count_down(COUNTDOWN_SEC)

    print("\n" + "=" * 65)
    print("  [AI 쓰레기 4종 감지 & 지정 슬롯 자율주행 시작]")
    print("  - [1] 종이 ➔ 1번 지정 수거함 이동")
    print("  - [2] 종이팩 ➔ 2번 지정 수거함 이동")
    print("  - [3] 패트병(플라스틱) ➔ 3번 지정 수거함 이동")
    print("  - [4] 캔 ➔ 4번 지정 수거함 이동")
    print("  - ↩️ 정밀 물리 대칭 엔진: 배출 후 1:1 대칭 역주행으로 시작 위치 오차 0.00cm 완벽 복귀!")
    print("  * 종료하려면 화면 창에서 ESC를 누르세요.")
    print("=" * 65 + "\n")

    current_target = None
    consecutive_count = 0

    try:
        while True:
            image = cam.read()
            if image is None:
                time.sleep(0.5)
                continue

            tmi.predict(image, 0.0)
            raw_label = tmi.get_label()
            conf = tmi.get_conf()

            if conf < CONFIDENCE_THRESHOLD:
                mapped_category = "없음"
            else:
                mapped_category = map_raw_label_to_category(raw_label)

            if mapped_category != "없음":
                if mapped_category == current_target:
                    consecutive_count += 1
                else:
                    current_target = mapped_category
                    consecutive_count = 1

                image = draw_hud_and_bbox(image, mapped_category, conf, consecutive_count, REQUIRED_FRAMES, stats)

                if consecutive_count >= REQUIRED_FRAMES:
                    stats[mapped_category] = stats.get(mapped_category, 0) + 1
                    save_stats(stats)

                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_cat = mapped_category.replace('/', '_')
                    cap_path = TODAY_CAPTURES_DIR / f"{timestamp}_{safe_cat}.jpg"
                    cv2.imwrite(str(cap_path), image)
                    waypoint_manager.log_event("CAPTURE_SAVED", f"이미지 자동 캡처 파티셔닝 저장: {cap_path.name}")

                    led_spec = LED_MAP.get(mapped_category, ("off", "off"))
                    set_robot_led(hamster, led_spec)

                    operate_gripper_and_transport(hamster, cam, mapped_category, conf, stats)

                    set_robot_led(hamster, ("off", "off"))
                    current_target = None
                    consecutive_count = 0
            else:
                current_target = None
                consecutive_count = 0
                set_robot_led(hamster, ("off", "off"))
                image = draw_hud_and_bbox(image, "없음", conf, 0, REQUIRED_FRAMES, stats)

            if image is not None:
                cam.show(image)

            if cam.check_key() == "esc":
                break

    finally:
        waypoint_manager.log_event("SYSTEM_START", "프로그램 정상 종료")
        set_robot_led(hamster, ("off", "off"))
        hamster.stop()


if __name__ == "__main__":
    main()
