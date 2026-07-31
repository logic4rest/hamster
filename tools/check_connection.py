"""
햄스터 로봇 연결 확인 스크립트
================================
BLE 동글과 햄스터 로봇이 제대로 연결됐는지,
기본 동작(LED / 소리 / 바퀴)이 모두 정상인지 단계적으로 점검합니다.

실행 방법:
    python tools/check_connection.py
    uv run python tools/check_connection.py
"""

import time
import sys

# ── 색상 출력 헬퍼 ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg: str):    print(f"  {GREEN}[OK]  {msg}{RESET}")
def fail(msg: str):  print(f"  {RED}[FAIL]  {msg}{RESET}")
def info(msg: str):  print(f"  {CYAN}[INFO]  {msg}{RESET}")
def warn(msg: str):  print(f"  {YELLOW}[WARN]  {msg}{RESET}")
def step(n: int, msg: str):
    print(f"\n{BOLD}[{n}/5] {msg}{RESET}")

# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{'='*50}")
    print("  햄스터 로봇 연결 & 동작 점검")
    print(f"{'='*50}{RESET}")

    # ── Step 1: roboid 라이브러리 임포트 ──────────────────────────────────────
    step(1, "roboid 라이브러리 로드")
    try:
        from roboid import Hamster, wait
        ok("roboid 임포트 성공")
    except ImportError as e:
        fail(f"roboid 임포트 실패: {e}")
        print(f"\n  {YELLOW}해결 방법:{RESET}")
        print("    pip install -U roboid")
        sys.exit(1)

    # ── Step 2: 햄스터 연결 ───────────────────────────────────────────────────
    step(2, "햄스터 BLE 연결")
    info("BLE 동글이 꽂혀 있고 로봇 전원이 켜져 있는지 확인하세요.")
    info("연결 중... (최대 10초 소요)")
    try:
        hamster = Hamster()
        time.sleep(2)
        ok("햄스터 연결 성공!")
    except Exception as e:
        fail(f"연결 실패: {e}")
        print(f"\n  {YELLOW}확인 사항:{RESET}")
        print("    - BLE USB 동글이 PC에 꽂혀 있나요?")
        print("    - 햄스터 로봇 전원이 켜져 있나요?")
        print("    - 동글 드라이버가 장치 관리자에서 정상인가요?")
        print("    - 다른 프로그램이 동글을 점유 중이지 않나요?")
        sys.exit(1)

    all_passed = True

    # ── Step 3: LED 점검 ──────────────────────────────────────────────────────
    step(3, "LED 점검")
    try:
        info("왼쪽 LED: 빨강")
        hamster.leds("RED", "OFF")
        time.sleep(0.6)

        info("오른쪽 LED: 파랑")
        hamster.leds("OFF", "BLUE")
        time.sleep(0.6)

        info("양쪽 LED: 초록")
        hamster.leds("GREEN", "GREEN")
        time.sleep(0.6)

        hamster.leds("OFF", "OFF")
        ok("LED 점검 완료 - 빨강/파랑/초록 순서로 점등되었나요?")
    except Exception as e:
        fail(f"LED 점검 실패: {e}")
        all_passed = False

    # ── Step 4: 부저(소리) 점검 ───────────────────────────────────────────────
    step(4, "부저(소리) 점검")
    try:
        info("삐~ 소리가 나야 합니다")
        hamster.beep()
        time.sleep(1.0)
        ok("소리 점검 완료 - 소리가 들렸나요?")
    except Exception as e:
        fail(f"소리 점검 실패: {e}")
        all_passed = False

    # ── Step 5: 바퀴 점검 ────────────────────────────────────────────────────
    step(5, "바퀴 점검")
    warn("로봇이 잠시 움직입니다. 바닥에 놓아 주세요!")
    time.sleep(1.5)

    try:
        info("전진 (0.5초)")
        hamster.wheels(40, 40)
        time.sleep(0.5)
        hamster.stop()
        time.sleep(0.4)

        info("후진 (0.5초)")
        hamster.wheels(-40, -40)
        time.sleep(0.5)
        hamster.stop()
        time.sleep(0.4)

        info("좌회전 (0.5초)")
        hamster.wheels(-30, 30)
        time.sleep(0.5)
        hamster.stop()
        time.sleep(0.4)

        info("우회전 (0.5초)")
        hamster.wheels(30, -30)
        time.sleep(0.5)
        hamster.stop()

        ok("바퀴 점검 완료 - 전진/후진/좌회전/우회전이 동작했나요?")
    except Exception as e:
        fail(f"바퀴 점검 실패: {e}")
        all_passed = False

    # ── 최종 결과 ─────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*50}{RESET}")
    if all_passed:
        print(f"{GREEN}{BOLD}  [OK]  모든 점검 통과! 로봇이 정상입니다.{RESET}")
    else:
        print(f"{YELLOW}{BOLD}  [WARN]  일부 항목에서 문제가 발생했습니다.{RESET}")
        print(f"  AGENTS.md 의 '흔한 문제 해결' 섹션을 참고하세요.")
    print(f"{BOLD}{'='*50}{RESET}\n")

    hamster.stop()


if __name__ == "__main__":
    main()
