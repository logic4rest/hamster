"""
쓰레기 4종 위치 번호별 저장 및 V6.3 정밀 역주행 복귀 학습 도구 (v6.3 엣지 트리가 에디션)
====================================================================================================
키 조종 안내:
  - 🕹️ 화살표 키(↑, ↓, ←, →): 로봇 이동 조종
  - 🦾 Enter 또는 C: 실물 집게 접기 / 닫기 (CLOSE)
  - 🦾 Spacebar 또는 O: 실물 집게 펼치기 / 열기 (OPEN)
  - 🏁 Q 키 또는 ESC: 도착 완주 및 0.00cm 대칭 정밀 역주행 복귀 저장

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
    """지정된 슬롯 번호(1~4) 위치 키보드 조종 및 역주행 복귀 테스트"""
    slot_name = NUMBERED_SLOTS.get(slot_num, "종이")

    print(f"\n{BOLD}{'='*65}")
    print(f"  🎮 슬롯 [{slot_num}] '{slot_name}' 위치 키보드 조종 학습")
    print(f"{'='*65}{RESET}\n")

    print(f"  1. 햄스터를 {YELLOW}시작 위치(카메라 앞){RESET}에 놓아주세요.")
    print(f"  2. {CYAN}화살표 키(↑, ↓, ←, →){RESET}로 로봇을 조종하여 {YELLOW}[{slot_num}] '{slot_name}' 수거함 위치{RESET}까지 이동하세요.")
    print(f"  3. 🦾 {GREEN}Enter 또는 C{RESET}: 집게 접기/닫기  |  🦾 {CYAN}Space 또는 O{RESET}: 집게 펼치기/열기")
    print(f"  4. 도착하면 {GREEN}Q 키 또는 ESC{RESET}를 누르면 저장 후 시작 위치로 대칭 복귀합니다.\n")

    while keyboard.is_pressed("enter") or keyboard.is_pressed("space") or keyboard.is_pressed("q") or keyboard.is_pressed("esc"):
        time.sleep(0.05)
    time.sleep(0.2)

    hamster.leds("yellow", "yellow")
    hamster.beep()

    route_steps = []
    cur_left, cur_right = 0, 0
    step_start_time = time.time()
    poll_interval = 0.04

    prev_enter = False
    prev_space = False

    print(f"{YELLOW}>>> Enter/C:집게접기 | Space/O:집게펼치기 | Q/ESC:도착완료저장 <<<{RESET}\n")

    try:
        while True:
            # 🏁 완료 종료 (Q, ESC 또는 F)
            if keyboard.is_pressed("q") or keyboard.is_pressed("esc") or keyboard.is_pressed("f"):
                dur = time.time() - step_start_time
                if cur_left != 0 or cur_right != 0:
                    route_steps.append({"left": cur_left, "right": cur_right, "duration": dur})
                break

            # 💡 엣지 트리거 (Edge Triggering) - 키를 꾹 누르고 있어도 단 1회만 동작!
            curr_enter = keyboard.is_pressed("enter") or keyboard.is_pressed("c")
            curr_space = keyboard.is_pressed("space") or keyboard.is_pressed("o")

            if curr_enter and not prev_enter:
                control_gripper(hamster, "close")
                print(f"\n  🦾 [집게 제어] Enter/C ➔ 집게 접기/닫기 (CLOSE)")
            elif curr_space and not prev_space:
                control_gripper(hamster, "open")
                print(f"\n  🦾 [집게 제어] Spacebar/O ➔ 집게 펼치기/열기 (OPEN)")

            prev_enter = curr_enter
            prev_space = curr_space

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

    # V6.3 Zero-Slip 정밀 역주행 복귀
    print(f"\n{CYAN}>>> [Zero-Slip V6.3 복귀] 저장된 데이터의 역방향으로 시작 위치로 복귀합니다... <<<{RESET}")
    hamster.beep()
    time.sleep(0.5)

    reverse_route = waypoint_manager.get_reverse_return_trajectory(trajectory)
    for s in reverse_route:
        hamster.wheels(s["left"], s["right"])
        time.sleep(s["duration"])

    hamster.stop()
    hamster.leds("off", "off")
    print(f"\n{GREEN}{BOLD}🎉 슬롯 [{slot_num}] '{slot_name}' 위치 저장 및 정밀 복귀 완료!{RESET}\n")
    return saved_info


def main():
    print(f"\n{BOLD}{'='*65}")
    print("  🐹 쓰레기 4종 위치 번호별 지정 저장 도구 (v6.3 엣지트리거)")
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
