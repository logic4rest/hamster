"""
쓰레기 4종 위치 번호별 저장 및 조종 학습 도구 (v4.2)
====================================================================================================
4종 슬롯 매핑:
  [1] 종이
  [2] 종이팩
  [3] 패트병(플라스틱)
  [4] 캔

실행 방법:
    python tools/record_paper_path.py
    uv run python tools/record_paper_path.py
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

import keyboard
from roboid import Hamster

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hamster.waypoint_manager import waypoint_manager, NUMBERED_SLOTS

GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
BOLD    = "\033[1m"
RESET   = "\033[0m"
CLEAR_LINE = "\033[2K\r"


def control_gripper(hamster, action: str):
    try:
        if action == "open":
            if hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(0)
        elif action == "close":
            if hasattr(hamster, "close_gripper"):
                hamster.close_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(100)
        elif action == "release":
            if hasattr(hamster, "release_gripper"):
                hamster.release_gripper()
            elif hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
    except Exception:
        pass


def get_steer(kb):
    """화살표 키(또는 WASD) 입력에 따른 (left_speed, right_speed, mode_name) 반환"""
    speed = 35
    mode_name = "보통(35)"
    if kb.is_pressed("shift"):
        speed = 50
        mode_name = "고속(50)"
    elif kb.is_pressed("ctrl"):
        speed = 25
        mode_name = "저속(25)"

    up    = kb.is_pressed("up")    or kb.is_pressed("w")
    down  = kb.is_pressed("down")  or kb.is_pressed("s")
    left  = kb.is_pressed("left")  or kb.is_pressed("a")
    right = kb.is_pressed("right") or kb.is_pressed("d")

    if up and down:
        up = down = False
    if left and right:
        left = right = False

    if up and left:
        return int(speed * 0.4), speed, f"↖ 좌전진 [{mode_name}]"
    if up and right:
        return speed, int(speed * 0.4), f"↗ 우전진 [{mode_name}]"
    if up:
        return speed, speed, f"▲ 전진 [{mode_name}]"
    if down and left:
        return -int(speed * 0.4), -speed, f"↙ 좌후진 [{mode_name}]"
    if down and right:
        return -speed, -int(speed * 0.4), f"↘ 우후진 [{mode_name}]"
    if down:
        return -speed, -speed, f"▼ 후진 [{mode_name}]"
    if left:
        return -speed, speed, f"↺ 좌회전 [{mode_name}]"
    if right:
        return speed, -speed, f"↻ 우회전 [{mode_name}]"

    return 0, 0, "■ 정지"


def record_slot_session(hamster, slot_num: str):
    """지정된 슬롯 번호(1~4) 위치 화살표 키 조종 및 역주행 복귀 테스트"""
    slot_name = NUMBERED_SLOTS.get(slot_num, "종이")

    print(f"\n{BOLD}{'='*65}")
    print(f"  🎮 슬롯 [{slot_num}] '{slot_name}' 위치 화살표 키 조종 학습")
    print(f"{'='*65}{RESET}\n")

    print(f"  1. 햄스터를 {YELLOW}시작 위치(카메라 앞){RESET}에 놓아주세요.")
    print(f"  2. {CYAN}화살표 키(↑, ↓, ←, →){RESET}로 로봇을 조종하여 {YELLOW}[{slot_num}] '{slot_name}' 수거함 위치{RESET}까지 이동하세요.")
    print(f"  3. 도착하면 {GREEN}Enter(엔터){RESET} 키를 누르면 슬롯 [{slot_num}]번에 즉시 저장됩니다.")
    print(f"  4. 저장이 완료되면 로봇이 자동으로 원래 시작 위치로 역주행 복귀합니다.\n")

    hamster.leds("yellow", "yellow")
    hamster.beep()

    route_steps = []
    cur_left, cur_right = 0, 0
    step_start_time = time.time()
    poll_interval = 0.04

    print(f"{YELLOW}>>> 화살표 키로 [{slot_num}] '{slot_name}' 위치까지 조종하세요! (도착 시 Enter) <<<{RESET}\n")

    try:
        while True:
            if keyboard.is_pressed("esc") or keyboard.is_pressed("q"):
                print(f"\n{YELLOW}[취소] 슬롯 [{slot_num}] 학습을 취소합니다.{RESET}")
                hamster.stop()
                hamster.leds("off", "off")
                return None

            if keyboard.is_pressed("enter") or keyboard.is_pressed("space"):
                dur = time.time() - step_start_time
                if cur_left != 0 or cur_right != 0:
                    route_steps.append({"left": cur_left, "right": cur_right, "duration": dur})
                break

            if keyboard.is_pressed("o"):
                control_gripper(hamster, "open")
                print(f"{CLEAR_LINE}  🦾 집게 열기 (OPEN)", end="", flush=True)
                time.sleep(0.15)
            elif keyboard.is_pressed("c"):
                control_gripper(hamster, "close")
                print(f"{CLEAR_LINE}  🦾 집게 닫기 (CLOSE)", end="", flush=True)
                time.sleep(0.15)

            new_left, new_right, label = get_steer(keyboard)

            if (new_left, new_right) != (cur_left, cur_right):
                dur = time.time() - step_start_time
                if dur > 0.03 and (cur_left != 0 or cur_right != 0):
                    route_steps.append({"left": cur_left, "right": cur_right, "duration": dur})

                cur_left, cur_right = new_left, new_right
                step_start_time = time.time()

                if cur_left == 0 and cur_right == 0:
                    hamster.stop()
                else:
                    hamster.wheels(cur_left, cur_right)

                print(f"{CLEAR_LINE}  [기록 중] 동작: {label} (스텝: {len(route_steps)}개)", end="", flush=True)

            time.sleep(poll_interval)

    finally:
        hamster.stop()

    # 슬롯 번호 저장
    saved_info = waypoint_manager.save_slot(slot_num, route_steps)
    trajectory = saved_info["trajectory"]

    print(f"\n\n{GREEN}[저장 완료] 슬롯 [{slot_num}] '{slot_name}' 위치가 성공적으로 저장되었습니다! ({len(trajectory)}단계){RESET}")

    # 자동 역주행 복귀
    print(f"\n{CYAN}>>> [자동 복귀] 저장된 데이터의 역방향으로 시작 위치로 복귀합니다... <<<{RESET}")
    hamster.beep()
    time.sleep(0.5)

    for s in reversed(trajectory):
        hamster.wheels(-s["left"], -s["right"])
        time.sleep(s["duration"])

    hamster.stop()
    hamster.leds("off", "off")
    print(f"\n{GREEN}{BOLD}🎉 슬롯 [{slot_num}] '{slot_name}' 위치 저장 및 복귀 완료!{RESET}\n")
    return saved_info


def main():
    print(f"\n{BOLD}{'='*65}")
    print("  🐹 쓰레기 4종 위치 번호별 지정 저장 도구 (v4.2)")
    print(f"{'='*65}{RESET}\n")

    print("[INFO] 햄스터 로봇 연결 중...")
    try:
        hamster = Hamster()
        time.sleep(1.5)
        print(f"{GREEN}[OK] 햄스터 로봇 연결 성공!{RESET}\n")
    except Exception as e:
        print(f"{RED}[FAIL] 로봇 연결 실패: {e}{RESET}")
        sys.exit(1)

    while True:
        print(f"{BOLD}저장할 쓰레기 항목의 번호(1~4)를 선택하세요:{RESET}")
        print("  [1] 📄 종이")
        print("  [2] 🩵 종이팩")
        print("  [3] 🥤 패트병(플라스틱)")
        print("  [4] 🥫 캔")
        print("  [0] 🚀 학습 완료 및 카메라 AI 자율주행 실행 준비\n")

        choice = input("번호 선택 (1, 2, 3, 4) > ").strip()

        if choice == "0":
            print(f"\n{GREEN}✔ 4종 슬롯 설정 완료! 'uv run python main.py'를 실행하여 카메라 자율주행을 시작하세요.{RESET}")
            break

        if choice in NUMBERED_SLOTS:
            record_slot_session(hamster, choice)
        else:
            print(f"{RED}잘못된 번호입니다. 1, 2, 3, 4 중에서 선택해 주세요.{RESET}\n")


if __name__ == "__main__":
    main()
