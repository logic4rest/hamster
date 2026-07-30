"""
햄스터 로봇 키보드 조종 스크립트
====================================
방향키 또는 WASD 키로 햄스터 로봇을 실시간으로 조종합니다.

  조작키:
    W / ↑        전진
    S / ↓        후진
    A / ←        좌회전
    D / →        우회전
    W+A / ↑+←    전진하면서 좌로 꺾기
    W+D / ↑+→    전진하면서 우로 꺾기
    S+A / ↓+←    후진하면서 좌로 꺾기
    S+D / ↓+→    후진하면서 우로 꺾기
    Space        정지
    Q / ESC      프로그램 종료

요구 라이브러리:
    pip install keyboard
    (또는 uv add keyboard)

주의: Windows 에서 keyboard 라이브러리는 관리자 권한 없이도 동작하지만,
      일부 환경에서는 관리자 권한으로 실행해야 할 수 있습니다.

실행 방법:
    python tools/keyboard_control.py
    uv run python tools/keyboard_control.py
"""

import sys
import time

# ── 색상 출력 헬퍼 ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAGENTA= "\033[95m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CLEAR_LINE = "\033[2K\r"

def err(msg: str):  print(f"{RED}✘  {msg}{RESET}")
def info(msg: str): print(f"{CYAN}→  {msg}{RESET}")

# ── 설정 ─────────────────────────────────────────────────────────────────────
SPEED_STRAIGHT  = 60   # 직진 속도
SPEED_TURN      = 40   # 회전 속도 (한 바퀴만 구동)
SPEED_CURVE_FAST  = 60 # 커브 빠른 쪽
SPEED_CURVE_SLOW  = 25 # 커브 느린 쪽
POLL_INTERVAL   = 0.05 # 키 상태 확인 주기 (초) — 낮을수록 반응 빠름

# ── 라이브러리 임포트 ─────────────────────────────────────────────────────────
def import_keyboard():
    try:
        import keyboard
        return keyboard
    except ImportError:
        err("keyboard 라이브러리가 없습니다.")
        print("  설치 명령: pip install keyboard")
        sys.exit(1)

def import_roboid():
    try:
        from roboid import Hamster
        return Hamster
    except ImportError:
        err("roboid 라이브러리가 없습니다.")
        print("  설치 명령: pip install roboid")
        sys.exit(1)

# ── 키 상태 읽기 ──────────────────────────────────────────────────────────────
def get_direction(kb) -> tuple[int, int]:
    """
    현재 눌린 키 조합을 읽어 (left_wheel, right_wheel) 속도를 반환한다.
    반환값 범위: -100 ~ 100
    """
    up    = kb.is_pressed("up")    or kb.is_pressed("w")
    down  = kb.is_pressed("down")  or kb.is_pressed("s")
    left  = kb.is_pressed("left")  or kb.is_pressed("a")
    right = kb.is_pressed("right") or kb.is_pressed("d")

    # 상하 동시 입력 → 무시
    if up and down:
        up = down = False
    # 좌우 동시 입력 → 무시
    if left and right:
        left = right = False

    # ── 전진 계열 ─────────────────────────────────────────────────────────────
    if up and left:
        return SPEED_CURVE_SLOW, SPEED_CURVE_FAST   # 전진 좌 커브
    if up and right:
        return SPEED_CURVE_FAST, SPEED_CURVE_SLOW   # 전진 우 커브
    if up:
        return SPEED_STRAIGHT, SPEED_STRAIGHT        # 직진

    # ── 후진 계열 ─────────────────────────────────────────────────────────────
    if down and left:
        return -SPEED_CURVE_SLOW, -SPEED_CURVE_FAST  # 후진 좌 커브
    if down and right:
        return -SPEED_CURVE_FAST, -SPEED_CURVE_SLOW  # 후진 우 커브
    if down:
        return -SPEED_STRAIGHT, -SPEED_STRAIGHT       # 직진 후진

    # ── 제자리 회전 ───────────────────────────────────────────────────────────
    if left:
        return -SPEED_TURN, SPEED_TURN               # 제자리 좌회전
    if right:
        return SPEED_TURN, -SPEED_TURN               # 제자리 우회전

    return 0, 0  # 아무 키도 안 눌림 → 정지

def action_label(left: int, right: int) -> str:
    """바퀴 속도를 보기 좋은 문자열로 변환한다."""
    if left == 0 and right == 0:
        return f"{YELLOW}■ 정지{RESET}"
    if left > 0 and right > 0:
        if left == right:
            return f"{GREEN}▲ 전진  ({left}){RESET}"
        elif left < right:
            return f"{GREEN}↗ 전진+우  (L={left} R={right}){RESET}"
        else:
            return f"{GREEN}↖ 전진+좌  (L={left} R={right}){RESET}"
    if left < 0 and right < 0:
        if left == right:
            return f"{MAGENTA}▼ 후진  ({abs(left)}){RESET}"
        elif abs(left) < abs(right):
            return f"{MAGENTA}↙ 후진+좌  (L={left} R={right}){RESET}"
        else:
            return f"{MAGENTA}↘ 후진+우  (L={left} R={right}){RESET}"
    if left < 0 and right > 0:
        return f"{CYAN}↺ 좌회전  (L={left} R={right}){RESET}"
    if left > 0 and right < 0:
        return f"{CYAN}↻ 우회전  (L={left} R={right}){RESET}"
    return f"L={left} R={right}"

# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    kb = import_keyboard()
    HamsterClass = import_roboid()

    print(f"\n{BOLD}{'='*54}")
    print("   🐹 햄스터 키보드 조종기")
    print(f"{'='*54}{RESET}")
    print()
    print("  조작키:")
    print(f"    {BOLD}W / ↑{RESET}        전진")
    print(f"    {BOLD}S / ↓{RESET}        후진")
    print(f"    {BOLD}A / ←{RESET}        좌회전")
    print(f"    {BOLD}D / →{RESET}        우회전")
    print(f"    {BOLD}W+A · W+D{RESET}    전진 커브")
    print(f"    {BOLD}S+A · S+D{RESET}    후진 커브")
    print(f"    {BOLD}Space{RESET}         강제 정지")
    print(f"    {BOLD}Q / ESC{RESET}      종료")
    print()

    info("햄스터에 연결 중... (BLE 동글과 로봇 전원을 확인하세요)")
    try:
        hamster = HamsterClass()
        time.sleep(1.5)
    except Exception as e:
        err(f"연결 실패: {e}")
        print("  tools/check_connection.py 를 먼저 실행해 보세요.")
        sys.exit(1)

    print(f"{GREEN}✔  연결 성공! 조종을 시작합니다.{RESET}")
    print(f"{YELLOW}   키에서 손을 떼면 자동으로 정지합니다.{RESET}\n")
    print("-" * 54)

    prev_left, prev_right = None, None  # 이전 상태 기억 (불필요한 명령 방지)

    try:
        while True:
            # 종료 키 확인
            if kb.is_pressed("q") or kb.is_pressed("esc"):
                break

            # 강제 정지 키
            if kb.is_pressed("space"):
                left, right = 0, 0
            else:
                left, right = get_direction(kb)

            # 상태가 바뀔 때만 로봇에 명령 전송 (불필요한 BLE 트래픽 방지)
            if (left, right) != (prev_left, prev_right):
                if left == 0 and right == 0:
                    hamster.stop()
                else:
                    hamster.wheels(left, right)
                prev_left, prev_right = left, right

                # 현재 동작 출력 (같은 줄에 덮어쓰기)
                label = action_label(left, right)
                print(f"{CLEAR_LINE}  상태: {label}", end="", flush=True)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n\n{BOLD}[종료]{RESET} 정지 명령을 보내고 연결을 끊습니다...")
        hamster.stop()
        time.sleep(0.3)
        print(f"{GREEN}✔  정상 종료{RESET}\n")


if __name__ == "__main__":
    main()
