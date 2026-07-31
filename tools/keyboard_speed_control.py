"""
햄스터 로봇 가변 속도 키보드 조종 스크립트
==============================================
방향키 또는 WASD 키로 햄스터 로봇을 실시간으로 조종합니다.
Shift 키로 속도를 올리고, Ctrl 키로 속도를 줄일 수 있습니다.

  조작키:
    W / ↑        전진
    S / ↓        후진
    A / ←        좌회전
    D / →        우회전
    Shift        고속 모드 (🚀 직진 100 / 회전 70)
    Ctrl         저속 모드 (🐢 직진 30 / 회전 20)
    (기본값)     보통 모드 (🚗 직진 60 / 회전 40)
    Space        강제 정지
    Q / ESC      프로그램 종료

요구 라이브러리:
    pip install keyboard roboid

실행 방법:
    python tools/keyboard_speed_control.py
    uv run python tools/keyboard_speed_control.py
"""

import sys
import time

# ── 색상 및 포맷 헬퍼 ─────────────────────────────────────────────────────────
GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
BOLD    = "\033[1m"
RESET   = "\033[0m"
CLEAR_LINE = "\033[2K\r"

def err(msg: str):  print(f"{RED}✘  {msg}{RESET}")
def info(msg: str): print(f"{CYAN}→  {msg}{RESET}")

# ── 속도 설정 ─────────────────────────────────────────────────────────────────
# (직진속도, 회전속도, 커브 빠른쪽, 커브 느린쪽)
SPEED_MODES = {
    "FAST":   {"name": "🚀 고속", "straight": 100, "turn": 70, "curve_fast": 100, "curve_slow": 40},
    "NORMAL": {"name": "🚗 보통", "straight": 60,  "turn": 40, "curve_fast": 60,  "curve_slow": 25},
    "SLOW":   {"name": "🐢 저속", "straight": 30,  "turn": 20, "curve_fast": 30,  "curve_slow": 10},
}

POLL_INTERVAL = 0.05  # 키 상태 확인 주기 (초)

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

# ── 속도 모드 판별 ────────────────────────────────────────────────────────────
def get_speed_mode(kb) -> dict:
    """Shift/Ctrl 키 상태에 따른 속도 설정 객체를 반환한다."""
    shift = kb.is_pressed("shift")
    ctrl  = kb.is_pressed("ctrl")

    # Shift와 Ctrl이 모두 눌렸거나 둘 다 안 눌린 경우 -> 보통 속도 (상쇄)
    if shift and ctrl:
        return SPEED_MODES["NORMAL"]
    elif shift:
        return SPEED_MODES["FAST"]
    elif ctrl:
        return SPEED_MODES["SLOW"]
    else:
        return SPEED_MODES["NORMAL"]

# ── 키 상태 읽기 ──────────────────────────────────────────────────────────────
def get_direction(kb) -> tuple[int, int, str]:
    """
    현재 눌린 키 조합 및 속도 조절 키를 읽어 (left_wheel, right_wheel, mode_name)을 반환한다.
    """
    mode = get_speed_mode(kb)

    straight   = mode["straight"]
    turn       = mode["turn"]
    curve_fast = mode["curve_fast"]
    curve_slow = mode["curve_slow"]
    mode_name  = mode["name"]

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
        return curve_slow, curve_fast, mode_name
    if up and right:
        return curve_fast, curve_slow, mode_name
    if up:
        return straight, straight, mode_name

    # ── 후진 계열 ─────────────────────────────────────────────────────────────
    if down and left:
        return -curve_slow, -curve_fast, mode_name
    if down and right:
        return -curve_fast, -curve_slow, mode_name
    if down:
        return -straight, -straight, mode_name

    # ── 제자리 회전 ───────────────────────────────────────────────────────────
    if left:
        return -turn, turn, mode_name
    if right:
        return turn, -turn, mode_name

    return 0, 0, mode_name  # 정지

def action_label(left: int, right: int, mode_name: str) -> str:
    """바퀴 속도 및 모드를 보기 좋은 문자열로 변환한다."""
    if left == 0 and right == 0:
        return f"{YELLOW}■ 정지{RESET}  [{mode_name}]"
    if left > 0 and right > 0:
        if left == right:
            return f"{GREEN}▲ 전진  ({left}){RESET}  [{mode_name}]"
        elif left < right:
            return f"{GREEN}↗ 전진+우  (L={left} R={right}){RESET}  [{mode_name}]"
        else:
            return f"{GREEN}↖ 전진+좌  (L={left} R={right}){RESET}  [{mode_name}]"
    if left < 0 and right < 0:
        if left == right:
            return f"{MAGENTA}▼ 후진  ({abs(left)}){RESET}  [{mode_name}]"
        elif abs(left) < abs(right):
            return f"{MAGENTA}↙ 후진+좌  (L={left} R={right}){RESET}  [{mode_name}]"
        else:
            return f"{MAGENTA}↘ 후진+우  (L={left} R={right}){RESET}  [{mode_name}]"
    if left < 0 and right > 0:
        return f"{CYAN}↺ 좌회전  (L={left} R={right}){RESET}  [{mode_name}]"
    if left > 0 and right < 0:
        return f"{CYAN}↻ 우회전  (L={left} R={right}){RESET}  [{mode_name}]"
    return f"L={left} R={right}  [{mode_name}]"

# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    kb = import_keyboard()
    HamsterClass = import_roboid()

    print(f"\n{BOLD}{'='*60}")
    print("   🐹 햄스터 가변 속도 키보드 조종기")
    print(f"{'='*60}{RESET}")
    print()
    print("  기본 조작키:")
    print(f"    {BOLD}W / ↑{RESET}        전진")
    print(f"    {BOLD}S / ↓{RESET}        후진")
    print(f"    {BOLD}A / ←{RESET}        좌회전")
    print(f"    {BOLD}D / →{RESET}        우회전")
    print(f"    {BOLD}W+A · W+D{RESET}    전진 커브")
    print(f"    {BOLD}S+A · S+D{RESET}    후진 커브")
    print()
    print("  속도 조절키 (방향키와 함께 사용):")
    print(f"    {BOLD}Shift{RESET}        🚀 고속 모드 (직진 100 / 회전 70)")
    print(f"    {BOLD}(없음){RESET}       🚗 보통 모드 (직진 60  / 회전 40)")
    print(f"    {BOLD}Ctrl{RESET}         🐢 저속 모드 (직진 30  / 회전 20)")
    print()
    print("  기타 키:")
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
    print("-" * 60)

    prev_left, prev_right, prev_mode = None, None, None

    try:
        while True:
            # 종료 키 확인
            if kb.is_pressed("q") or kb.is_pressed("esc"):
                break

            # 강제 정지 키
            if kb.is_pressed("space"):
                mode_info = get_speed_mode(kb)
                left, right, mode_name = 0, 0, mode_info["name"]
            else:
                left, right, mode_name = get_direction(kb)

            # 바퀴 속도 또는 속도 모드가 변했을 때 로봇에 명령 전송
            if (left, right, mode_name) != (prev_left, prev_right, prev_mode):
                if left == 0 and right == 0:
                    hamster.stop()
                else:
                    hamster.wheels(left, right)
                prev_left, prev_right, prev_mode = left, right, mode_name

                # 현재 동작 및 속도 모드 출력
                label = action_label(left, right, mode_name)
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
