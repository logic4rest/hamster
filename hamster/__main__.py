"""
티처블 머신 쓰레기 분리배출 햄스터 봇 제어 (v4.2 4종 번호 지정 슬롯 저장 & 자율주행 에디션)
====================================================================================================
4종 지정 슬롯:
  [1] 종이
  [2] 종이팩
  [3] 패트병(플라스틱)
  [4] 캔

프로세스:
1. 번호 선택 (1:종이, 2:종이팩, 3:패트병, 4:캔) 후 화살표 키로 위치 이동
2. 도착 후 [Enter] 누르면 해당 번호 슬롯에 즉시 위치 저장 및 시작 위치 자동 복귀
3. 바로 웹캠 카메라 AI 감지 시작
4. 쓰레기 확인 시 해당 번호 슬롯에 저장된 위치로 자율 이동! (전방 센서 자동 우회 활성화)

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
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import roboidai as ai
from roboid import *

# 위치 북마크 및 로그 관리자 모듈 로드
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hamster.waypoint_manager import waypoint_manager, NUMBERED_SLOTS, ROUTES_DIR, CAPTURES_DIR, LOGS_DIR

# ── 설정 ──────────────────────────────────────────────────────────────────────
MODEL_DIR    = str(PROJECT_ROOT / "models")
TODAY_STR    = time.strftime("%Y%m%d")
TODAY_CAPTURES_DIR = CAPTURES_DIR / f"{TODAY_STR}_분리배출기록"
TODAY_CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

STATS_PATH   = PROJECT_ROOT / "stats.json"

CONFIDENCE_THRESHOLD       = 0.8   # 이 값 미만이면 폐기/대기 (없음 처리)
REQUIRED_FRAMES            = 4     # 연속 4프레임 동일 시 최종 확정
COUNTDOWN_SEC              = 2     # 시작 전 카운트다운 초
PROXIMITY_OBSTACLE_THRESH  = 35    # 전방 장애물 감지 센서 기준값 (0~100)

# ── 카테고리 및 LED 매핑 ──────────────────────────────────────────────────────
CATEGORY_MAP = {
    "무색 페트병, 무색플라스틱": "플라스틱/페트병",
    "유리병, 유리통": "유리병(별도 수거)",
    "캔": "캔",
    "종이": "종이",
    "종이팩": "종이팩",
    "없음": "없음",
    # 하위 호환 및 키워드 매핑
    "무색 페트병": "플라스틱/페트병",
    "플라스틱": "플라스틱/페트병",
    "패트병": "플라스틱/페트병",
    "유리병": "유리병(별도 수거)",
    "유리통": "유리병(별도 수거)",
    "병": "유리병(별도 수거)",
    "이물질": "이물질/경고",
    "라벨": "이물질/경고",
    "음식물": "이물질/경고",
    "얼음": "이물질/경고",
    "종이팩(우유팩)": "종이팩",
}

# 햄스터 로봇 LED 색상 매핑
LED_MAP = {
    "플라스틱/페트병": ("blue", "blue"),
    "유리병(별도 수거)": (255, 100, 0, 255, 100, 0),  # 주황색 (Orange RGB)
    "캔": ("green", "green"),
    "종이": ("yellow", "yellow"),
    "종이팩": ("cyan", "cyan"),
    "이물질/경고": ("red", "red"),
}

# 화면 오버레이 BGR 색상 매핑
COLOR_BGR_MAP = {
    "플라스틱/페트병": (255, 50, 0),     # 파란색 (BGR)
    "유리병(별도 수거)": (0, 140, 255),    # 선명한 주황색 (BGR)
    "캔": (0, 220, 0),                 # 초록색
    "종이": (0, 220, 255),               # 노란색
    "종이팩": (255, 235, 0),              # 하늘색
    "이물질/경고": (0, 0, 235),         # 빨간색 (BGR)
    "없음": (120, 120, 120),             # 회색
}

# 올바른 분리배출 꿀팁 & 안내문
RECYCLING_TIPS = {
    "플라스틱/페트병": "💡 [3번 패트병 슬롯 이동] 저장된 3번 위치로 이동하며 장애물 자동 우회!",
    "유리병(별도 수거)": "⚠️ 집게 동작: 유리 전용 수거함(우측)으로 집어서 운반합니다.",
    "캔": "💡 [4번 캔 슬롯 이동] 저장된 4번 위치로 이동하며 장애물 자동 우회!",
    "종이": "💡 [1번 종이 슬롯 이동] 저장된 1번 위치로 이동하며 장애물 자동 우회!",
    "종이팩": "💡 [2번 종이팩 슬롯 이동] 저장된 2번 위치로 이동하며 장애물 자동 우회!",
    "이물질/경고": "🚨 오배출 경고! 이물질을 먼저 세척하고 라벨을 떼어 버려주세요!",
    "없음": "💡 쓰레기를 카메라 중앙에 비춰주세요. (1:종이, 2:종이팩, 3:패트병, 4:캔)",
}


def set_robot_led(hamster, led_spec):
    if isinstance(led_spec, tuple) and len(led_spec) == 6:
        hamster.leds(led_spec[0], led_spec[1], led_spec[2], led_spec[3], led_spec[4], led_spec[5])
    elif isinstance(led_spec, tuple) and len(led_spec) == 2:
        hamster.leds(led_spec[0], led_spec[1])
    else:
        hamster.leds("off", "off")


def control_physical_gripper(hamster, action: str):
    if hamster is None:
        return
    try:
        if action == "open":
            if hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(0)
        elif action == "close" or action == "grip":
            if hasattr(hamster, "close_gripper"):
                hamster.close_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(100)
        elif action == "release":
            if hasattr(hamster, "release_gripper"):
                hamster.release_gripper()
            elif hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(0)
    except Exception:
        pass


# ── 통계 관리 함수 ───────────────────────────────────────────────────────────
def load_stats() -> dict:
    default_stats = {
        "플라스틱/페트병": 0,
        "유리병(별도 수거)": 0,
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


# ── 한글 텍스트 렌더링 헬퍼 ───────────────────────────────────────────────────
def put_korean_text(frame: np.ndarray, text: str, xy: tuple, font_size: int = 20, color_bgr: tuple = (255, 255, 255)) -> np.ndarray:
    if frame is None:
        return frame
    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    try:
        font = ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    color_rgb = (color_bgr[2], color_bgr[1], color_bgr[0])
    draw.text(xy, text, font=font, fill=color_rgb)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def map_raw_label_to_category(raw_label: str) -> str:
    if not raw_label or raw_label == "없음":
        return "없음"

    if raw_label in CATEGORY_MAP:
        return CATEGORY_MAP[raw_label]

    if any(k in raw_label for k in ["유리병", "유리통", "유리", "병"]):
        return "유리병(별도 수거)"
    elif "캔" in raw_label:
        return "캔"
    elif any(k in raw_label for k in ["이물질", "라벨", "음식물", "얼음"]):
        return "이물질/경고"
    elif any(k in raw_label for k in ["페트병", "패트병", "플라스틱"]):
        return "플라스틱/페트병"
    elif "종이팩" in raw_label or "우유팩" in raw_label:
        return "종이팩"
    elif "종이" in raw_label:
        return "종이"

    return "없음"


def draw_hud_and_bbox(frame: np.ndarray, category: str, conf: float, count: int, max_count: int, stats: dict, gripper_status: str = "") -> np.ndarray:
    if frame is None:
        return frame

    h, w, _ = frame.shape
    clean_category = category.replace("★ 확정: ", "")
    color = COLOR_BGR_MAP.get(clean_category, (120, 120, 120))

    # 1) Bounding Box 사각형
    x1, y1 = int(w * 0.15), int(h * 0.15)
    x2, y2 = int(w * 0.85), int(h * 0.80)
    thickness = 3 if count < max_count else 5
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # 2) 모서리 포인터 선
    c_len = int(min(w, h) * 0.06)
    cv2.line(frame, (x1, y1), (x1 + c_len, y1), color, thickness + 2)
    cv2.line(frame, (x1, y1), (x1, y1 + c_len), color, thickness + 2)
    cv2.line(frame, (x2, y1), (x2 - c_len, y1), color, thickness + 2)
    cv2.line(frame, (x2, y1), (x2, y1 + c_len), color, thickness + 2)
    cv2.line(frame, (x1, y2), (x1 + c_len, y2), color, thickness + 2)
    cv2.line(frame, (x1, y2), (x1, y2 - c_len), color, thickness + 2)
    cv2.line(frame, (x2, y2), (x2 - c_len, y2), color, thickness + 2)
    cv2.line(frame, (x2, y2), (x2, y2 - c_len), color, thickness + 2)

    # 3) 상태 오버레이
    if gripper_status:
        if "장애물" in gripper_status or "우회" in gripper_status:
            grip_label = f"⚠️ [전방 장애물 감지!] {gripper_status}"
            g_bg_color = (0, 140, 255)
        elif "GRIP" in gripper_status or "잡기" in gripper_status:
            cv2.rectangle(frame, (x1 - 30, y1), (x1, y2), (0, 0, 255), -1)
            cv2.rectangle(frame, (x2, y1), (x2 + 30, y2), (0, 0, 255), -1)
            grip_label = "🦾 [집게 제어] 쓰레기 포획 완료 (GRIP!)"
            g_bg_color = (0, 0, 200)
        elif "OPEN" in gripper_status or "열기" in gripper_status:
            cv2.rectangle(frame, (x1 - 45, y1), (x1 - 25, y2), (0, 255, 0), 4)
            cv2.rectangle(frame, (x2 + 25, y1), (x2 + 45, y2), (0, 255, 0), 4)
            grip_label = "🦾 [집게 제어] 집게 열림 (OPEN)"
            g_bg_color = (0, 180, 0)
        elif "슬롯" in gripper_status or "지정" in gripper_status:
            grip_label = f"🗺️ [지정 슬롯 자율이동] {gripper_status}"
            g_bg_color = (0, 120, 180)
        else:
            grip_label = f"🚚 [로봇 이동 모션] {gripper_status}"
            g_bg_color = (200, 100, 0)

        cv2.rectangle(frame, (x1 - 40, y2 + 10), (x2 + 40, y2 + 45), g_bg_color, -1)
        frame = put_korean_text(frame, grip_label, (x1 - 30, y2 + 15), font_size=16, color_bgr=(255, 255, 255))

    # 4) 상단 중앙 카테고리 태그 바
    if clean_category != "없음":
        if category.startswith("★ 확정:"):
            if clean_category == "이물질/경고":
                tag_text = "[경고] 오배출/이물질 감지!"
            elif clean_category == "종이":
                tag_text = "[확정] 종이 -> [1번 종이 슬롯] 자율주행!"
            elif clean_category == "종이팩":
                tag_text = "[확정] 종이팩 -> [2번 종이팩 슬롯] 자율주행!"
            elif clean_category == "플라스틱/페트병":
                tag_text = "[확정] 페트병 -> [3번 패트병 슬롯] 자율주행!"
            elif clean_category == "캔":
                tag_text = "[확정] 캔 -> [4번 캔 슬롯] 자율주행!"
            elif clean_category == "유리병(별도 수거)":
                tag_text = "[별도 배출] 유리병 -> 전용 수거함 이동!"
            else:
                tag_text = f"[정상] {clean_category} -> 집게 수거함 이동!"
        else:
            tag_text = f"{clean_category} | {conf:.0%} [{count}/{max_count}]"
    else:
        tag_text = "쓰레기 감지 대기 중... (1:종이, 2:종이팩, 3:패트병, 4:캔)"

    frame = put_korean_text(frame, tag_text, (x1 + 10, y1 - 32), font_size=18, color_bgr=color)

    # 5) 화면 하단 분리배출 안내 바
    tip_text = RECYCLING_TIPS.get(clean_category, RECYCLING_TIPS["없음"])
    bar_color = (0, 0, 180) if "경고" in clean_category or "이물질" in clean_category else (30, 30, 30)
    text_color = (255, 255, 255) if "경고" in clean_category or "이물질" in clean_category else (0, 255, 255)
    cv2.rectangle(frame, (0, h - 45), (w, h), bar_color, -1)
    frame = put_korean_text(frame, tip_text, (15, h - 38), font_size=15, color_bgr=text_color)

    # 6) 우측 상단 실시간 수거 통계 HUD
    stats_str = f"[통계] 총 {stats['total']}개 | 플라스틱:{stats.get('플라스틱/페트병', 0)}  유리:{stats.get('유리병(별도 수거)', 0)}  캔:{stats.get('캔', 0)}  종이:{stats.get('종이', 0)}  종이팩:{stats.get('종이팩', 0)}  경고:{stats.get('이물질/경고', 0)}"
    cv2.rectangle(frame, (0, 0), (w, 35), (20, 20, 20), -1)
    frame = put_korean_text(frame, stats_str, (10, 6), font_size=13, color_bgr=(255, 255, 255))

    return frame


def drive_with_obstacle_avoidance(hamster, left_spd: int, right_spd: int, duration_sec: float, update_screen_func=None):
    """전방 적외선 센서를 실시간 감지하여 물건/장애물이 있으면 자동으로 우회 주행"""
    start_t = time.time()
    while time.time() - start_t < duration_sec:
        if left_spd > 0 and right_spd > 0:
            try:
                lp = hamster.left_proximity()
                rp = hamster.right_proximity()
            except Exception:
                lp, rp = 0, 0

            if lp > PROXIMITY_OBSTACLE_THRESH or rp > PROXIMITY_OBSTACLE_THRESH:
                waypoint_manager.log_event("OBSTACLE_DETECTED", f"전방 장애물 탐지 (좌:{lp}, 우:{rp}) -> 회피 우회 시작")
                if update_screen_func:
                    update_screen_func("⚠️ 전방 물건 감지! 우회 회피 주행 중...", 0.2)

                hamster.leds("yellow", "yellow")
                try:
                    hamster.beep()
                except Exception:
                    pass

                if lp >= rp:
                    hamster.wheels(40, -15)
                    time.sleep(0.45)
                    hamster.wheels(35, 35)
                    time.sleep(0.55)
                    hamster.wheels(-15, 40)
                    time.sleep(0.45)
                else:
                    hamster.wheels(-15, 40)
                    time.sleep(0.45)
                    hamster.wheels(35, 35)
                    time.sleep(0.55)
                    hamster.wheels(40, -15)
                    time.sleep(0.45)

                hamster.stop()
                if update_screen_func:
                    update_screen_func("✅ 우회 완료! 기존 경로 주행 재개", 0.3)

        hamster.wheels(left_spd, right_spd)
        if update_screen_func:
            update_screen_func("", 0.04)
        else:
            time.sleep(0.04)

    hamster.stop()


def initial_arrow_teach_session(hamster):
    """프로그램 시작 시 쓰레기 4종 지정 슬롯 위치 조종 학습"""
    print("\n" + "=" * 65)
    print("  🎮 [1단계] 쓰레기 4종 위치 번호별 지정 저장 세션")
    print("  [1] 📄 종이    [2] 🩵 종이팩    [3] 🥤 패트병(플라스틱)    [4] 캔")
    print("  - 저장하고자 하는 번호(1, 2, 3, 4)를 입력한 뒤 화살표 키로 조종하고 Enter!")
    print("  - 기존 보관된 4종 위치 데이터를 그대로 쓰시려면 지금 바로 Enter(또는 0)를 누르세요.")
    print("=" * 65)

    hamster.leds("yellow", "yellow")
    hamster.beep()

    steps = []
    cur_left, cur_right = 0, 0
    step_start_time = time.time()
    speed = 35

    print("\n>>> 지금 바로 엔터를 누르면 기존 4종 위치 유지, 1~4 입력 시 새로 저장합니다 <<<")

    try:
        while True:
            if keyboard.is_pressed("enter") or keyboard.is_pressed("space"):
                dur = time.time() - step_start_time
                if cur_left != 0 or cur_right != 0:
                    steps.append({"left": cur_left, "right": cur_right, "duration": dur})
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
        wp_info = waypoint_manager.save_slot("1", steps)  # 기본 1번 종이
        print(f"\n🎉 [위치 저장 완료!] 슬롯 [1] '종이' 위치 저장 ({wp_info['trajectory_steps']}단계 주행 기록)")
        print("↩️ 기억된 위치의 역방향으로 시작 위치로 자동 복귀합니다...")
        hamster.beep()
        for s in reversed(wp_info["trajectory"]):
            hamster.wheels(-s["left"], -s["right"])
            time.sleep(s["duration"])
        hamster.stop()
    else:
        waypoint_manager.log_event("SESSION", "기존 4종 위치 슬롯 유지")

    hamster.leds("off", "off")
    print("=" * 65 + "\n")


def operate_gripper_and_transport(hamster, cam, mapped_category: str, conf: float, stats: dict):
    """4종 지정 슬롯 및 전방 센서 우회 자율주행 통합 운반 시퀀스"""
    waypoint_manager.log_event("SORTING_START", f"분리배출 확정 시퀀스 시작: '{mapped_category}' (신뢰도: {conf:.2f})")

    # 매핑: 카테고리 ➔ 번호 슬롯 지정
    slot_map = {
        "종이": "1",
        "종이팩": "2",
        "플라스틱/페트병": "3",
        "캔": "4"
    }
    slot_id = slot_map.get(mapped_category, "1")

    def update_screen(status_msg: str, duration_sec: float):
        start = time.time()
        while time.time() - start < duration_sec:
            img = cam.read()
            if img is not None:
                img = draw_hud_and_bbox(img, f"★ 확정: {mapped_category}", conf, REQUIRED_FRAMES, REQUIRED_FRAMES, stats, status_msg)
                cam.show(img)
            if cam.check_key() == "esc":
                break

    # 1. 실물 집게 열기 & 접근 전진
    control_physical_gripper(hamster, "open")
    drive_with_obstacle_avoidance(hamster, 30, 30, 0.7, lambda msg, dur: update_screen(msg or "집게 열기 (OPEN) -> 접근 전진", dur))

    # 2. 실물 집게 닫기 (close_gripper)
    control_physical_gripper(hamster, "close")
    update_screen("쓰레기 포획 완료! (GRIP!)", 0.8)

    # 3. 4종 지정 번호 슬롯 위치 검색/호출 (Name/Slot Retrieval)
    named_route = waypoint_manager.get_waypoint(mapped_category)

    if named_route:
        waypoint_manager.log_event("AUTONOMOUS_NAV", f"슬롯 [{slot_id}] '{mapped_category}' 자율주행 실행 ({len(named_route)}단계)")
        for idx, step in enumerate(named_route, 1):
            drive_with_obstacle_avoidance(
                hamster, step["left"], step["right"], step["duration"],
                lambda msg, dur, i=idx: update_screen(msg or f"[{slot_id}번 {mapped_category}] 자율이동 중 [{i}/{len(named_route)}]", dur)
            )

    elif mapped_category == "유리병(별도 수거)":
        hamster.wheels(35, -35)
        update_screen("운반 중: 우회전 (유리 전용 수거함)", 0.8)
        drive_with_obstacle_avoidance(hamster, 35, 35, 0.7, lambda msg, dur: update_screen(msg or "운반 중: 전진 이동 (센서 우회 활성)", dur))

    elif mapped_category == "이물질/경고":
        waypoint_manager.log_event("WARNING_EVENT", "오배출/이물질 쓰레기 경고 발령")
        control_physical_gripper(hamster, "release")
        hamster.wheels(-30, -30)
        hamster.beep()
        update_screen("경고 오배출! 집게 해제 및 후진 퇴거", 0.8)
        hamster.stop()
        return

    hamster.stop()

    # 4. 실물 집게 해제 (release_gripper)
    control_physical_gripper(hamster, "release")
    update_screen("수거함 투입 완료! 집게 해제 (RELEASE)", 0.8)

    # 5. 원래 자리 복귀
    if named_route:
        for step in reversed(named_route):
            hamster.wheels(-step["left"], -step["right"])
            update_screen("지정 슬롯 역주행 복귀 중...", step["duration"])
        hamster.stop()
    else:
        hamster.wheels(-35, -35)
        update_screen("원래 위치로 후진 복귀 중...", 0.7)

        if mapped_category in ["플라스틱/페트병", "유리병(별도 수거)"]:
            hamster.wheels(35, -35)
            update_screen("시작 방향으로 회전 복귀", 0.6)
        elif mapped_category == "캔":
            hamster.wheels(-35, 35)
            update_screen("시작 방향으로 회전 복귀", 0.6)

    hamster.stop()
    update_screen("복귀 완료! 다음 쓰레기 감지 대기 중...", 0.5)
    waypoint_manager.log_event("SORTING_COMPLETE", f"분리배출 및 복귀 완료: [{slot_id}번 {mapped_category}]")


def open_camera():
    """안전한 카메라 연결 초기화"""
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
    waypoint_manager.log_event("SYSTEM_START", "AI 쓰레기 4종 지정 슬롯 스마트 자율주행 실행 (v4.2)")

    print(f"[INFO] 모델을 불러오는 중... ({MODEL_DIR})")
    tmi = ai.TmImage()
    tmi.load_model(MODEL_DIR)
    print("[INFO] 모델 로드 완료!")

    stats = load_stats()
    print(f"[INFO] 누적 분리배출 통계: {stats}")

    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()
    set_robot_led(hamster, ("off", "off"))

    # ★ 시작 즉시 쓰레기 4종 위치 지정 슬롯 학습 세션
    initial_arrow_teach_session(hamster)

    cam = open_camera()
    if cam is None:
        set_robot_led(hamster, ("off", "off"))
        hamster.stop()
        return

    print(f"[INFO] 카메라를 시작합니다 ({COUNTDOWN_SEC}초 카운트다운)...")
    cam.count_down(COUNTDOWN_SEC)

    print("\n" + "=" * 65)
    print("  [2단계: AI 쓰레기 4종 감지 & 지정 슬롯 자율주행 시작]")
    print("  - [1] 종이 ➔ 1번 위치 이동")
    print("  - [2] 종이팩 ➔ 2번 위치 이동")
    print("  - [3] 패트병(플라스틱) ➔ 3번 위치 이동")
    print("  - [4] 캔 ➔ 4번 위치 이동")
    print("  - 전방 센서 자동 우회: 이동 중 물건/장애물 발견 시 자동으로 회피 우회 주행!")
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

                # 4프레임 확정
                if consecutive_count >= REQUIRED_FRAMES:
                    # 통계 카운트 증가 & 저장
                    stats[mapped_category] = stats.get(mapped_category, 0) + 1
                    stats["total"] += 1
                    save_stats(stats)

                    # 확정 순간 날짜별 파티셔닝 저장
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_cat = mapped_category.replace('/', '_')
                    cap_path = TODAY_CAPTURES_DIR / f"{timestamp}_{safe_cat}.jpg"
                    cv2.imwrite(str(cap_path), image)
                    waypoint_manager.log_event("CAPTURE_SAVED", f"이미지 자동 캡처 파티셔닝 저장: {cap_path.name}")

                    # 1) 로봇 알림 LED 반응
                    led_spec = LED_MAP.get(mapped_category, ("off", "off"))
                    set_robot_led(hamster, led_spec)

                    # 2) 실물 집게 & 4종 지정 슬롯 자율주행 모션 실행 (전방 센서 우회 주행 포함!)
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
        waypoint_manager.log_event("SYSTEM_STOP", "프로그램 정상 종료")
        set_robot_led(hamster, ("off", "off"))
        hamster.stop()


if __name__ == "__main__":
    main()
