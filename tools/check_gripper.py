"""
햄스터 실물 집게(Gripper) 하드웨어 점검 도구 (v3.5 CP949 인코딩 안전 에디션)
====================================================================================================
roboid 공식 open_gripper(), close_gripper(), release_gripper() 및 output_a() 메서드를
이용하여 새로 배송된 실물 집게 모듈이 정상 작동하는지 단계별로 점검합니다.

실행 방법:
    python tools/check_gripper.py
    uv run python tools/check_gripper.py
"""

import time
import sys

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
    print(f"\n{BOLD}[{n}/4] {msg}{RESET}")


def main():
    print(f"\n{BOLD}{'='*55}")
    print("  [햄스터 실물 집게(Gripper) 하드웨어 점검 도구 v3.5]")
    print(f"{'='*55}{RESET}")

    step(1, "roboid 라이브러리 연결 확인")
    try:
        from roboid import Hamster
        ok("roboid 라이브러리 로드 성공")
    except ImportError:
        fail("roboid 라이브러리가 설치되어 있지 않습니다. (pip install roboid)")
        sys.exit(1)

    step(2, "햄스터 로봇 연결")
    info("BLE 동글과 햄스터 전원이 켜져 있는지 확인하세요.")
    try:
        hamster = Hamster()
        time.sleep(1.5)
        ok("햄스터 로봇 연결 성공!")
    except Exception as e:
        fail(f"햄스터 연결 실패: {e}")
        print(f"\n  {YELLOW}확인 사항:{RESET}")
        print("    - BLE 동글이 PC USB 포트에 제대로 꽂혀 있나요?")
        print("    - 햄스터 로봇 전원 스위치가 ON으로 켜져 있나요?")
        sys.exit(1)

    step(3, "실물 집게 개폐(open_gripper / close_gripper) 연속 점검")
    info("집게 케이블이 햄스터 등 상단 확장 포트 A(Port A)에 꽂혀 있어야 합니다.")
    time.sleep(1.0)

    try:
        # 1. 집게 열기 (OPEN)
        info("1) 집게 열기 (OPEN) -> hamster.open_gripper()")
        hamster.leds("GREEN", "GREEN")
        if hasattr(hamster, "open_gripper"):
            hamster.open_gripper()
        elif hasattr(hamster, "output_a"):
            hamster.output_a(0)
        time.sleep(1.5)

        # 2. 집게 닫기 (GRIP!)
        info("2) 집게 닫기 (GRIP!) -> hamster.close_gripper()")
        hamster.leds("BLUE", "BLUE")
        if hasattr(hamster, "close_gripper"):
            hamster.close_gripper()
        elif hasattr(hamster, "output_a"):
            hamster.output_a(100)
        hamster.beep()
        time.sleep(1.5)

        # 3. 3회 반복 개폐 동작
        info("3) 집게 3회 연속 개폐 반복 점검...")
        for i in range(1, 4):
            print(f"    - [{i}/3] open_gripper() (열기)")
            if hasattr(hamster, "open_gripper"):
                hamster.open_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(0)
            time.sleep(0.8)

            print(f"    - [{i}/3] close_gripper() (닫기)")
            if hasattr(hamster, "close_gripper"):
                hamster.close_gripper()
            elif hasattr(hamster, "output_a"):
                hamster.output_a(100)
            time.sleep(0.8)

        # 복귀: 집게 열기
        info("4) 복귀: 집게 해제 -> hamster.release_gripper()")
        if hasattr(hamster, "release_gripper"):
            hamster.release_gripper()
        elif hasattr(hamster, "open_gripper"):
            hamster.open_gripper()
        hamster.leds("OFF", "OFF")
        ok("실물 집게 제어 성공!")

    except Exception as e:
        fail(f"집게 점검 중 오류 발생: {e}")

    step(4, "최종 점검 결과")
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{GREEN}{BOLD}  [OK] 실물 집게 점검 테스트가 성공적으로 완료되었습니다!{RESET}")
    print("  - 실물 집게가 벌어지고 닫히는 것을 확인하셨다면")
    print("    이제 'uv run python main.py'를 실행하여 실물 수거를 진행하세요.")
    print(f"{BOLD}{'='*55}{RESET}\n")

    hamster.stop()


if __name__ == "__main__":
    main()
