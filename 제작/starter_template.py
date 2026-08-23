"""
🐹 햄스터 로봇 AI 스마트 프로젝트 개발자용 스타터 템플릿 (starter_template.py)
=============================================================================
이 파일은 다른 개발자나 사용자가 햄스터 로봇 모터, 집게, LED, 센서 및 카메라 AI를 
쉽게 제어하고 자신만의 새 프로젝트를 만들 수 있도록 설계된 주석 친화적 파이썬 스크립트입니다.

실행 방법:
    python 제작/starter_template.py
    uv run python 제작/starter_template.py
"""

import sys
import time
from pathlib import Path

# roboid 햄스터 로봇 제어 라이브러리
from roboid import Hamster

# ── 1. 글로벌 설정 ─────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.8  # 신뢰도 80% 이상 조건
REQUIRED_FRAMES = 6         # 연속 6프레임 확정 조건
WAIT_PLACEMENT_SEC = 4.0    # 쓰레기 4초 거치 대기 시간

# 쓰레기 카테고리별 햄스터 로봇 LED 색상 매핑
LED_MAP = {
    "플라스틱/페트병": ("blue", "blue"),
    "캔": ("green", "green"),
    "종이": ("yellow", "yellow"),
    "종이팩": ("white", "white"),
    "경고": ("red", "red"),
}


class HamsterBotController:
    """햄스터 로봇 모터, 집게, LED 통합 제어 클래스"""

    def __init__(self):
        print("[INFO] 햄스터 로봇 연결 중...")
        self.robot = Hamster()
        self.set_led("off", "off")
        print("[INFO] 햄스터 로봇 연결 완료!")

    def set_led(self, left_color: str, right_color: str):
        """로봇 5색 LED 점등 제어 (red, green, blue, yellow, cyan, magenta, white, off)"""
        try:
            self.robot.leds(left_color, right_color)
        except Exception as e:
            print(f"[WARN] LED 제어 오류: {e}")

    def control_gripper(self, action: str):
        """실물 집게 제어 (open: 펼치기 / close: 오므리기)"""
        try:
            if action in ["open", "release"]:
                if hasattr(self.robot, "open_gripper"):
                    self.robot.open_gripper()
                elif hasattr(self.robot, "output_a"):
                    self.robot.output_a(0)
                print("  🦾 [집게 제어] 집게 열기/펼침 (OPEN)")
            elif action in ["close", "grip"]:
                if hasattr(self.robot, "close_gripper"):
                    self.robot.close_gripper()
                elif hasattr(self.robot, "output_a"):
                    self.robot.output_a(100)
                print("  🦾 [집게 제어] 집게 닫기/오므림 (CLOSE)")
            time.sleep(0.7)  # 0.7초 확실한 물리 동작 대기
        except Exception as e:
            print(f"[WARN] 집게 제어 오류: {e}")

    def beep(self, count: int = 1):
        """부저 소리 발성"""
        for _ in range(count):
            try:
                self.robot.beep()
                time.sleep(0.15)
            except Exception:
                pass

    def drive_wheels(self, left_speed: int, right_speed: int, duration_sec: float):
        """양쪽 바퀴 속도 지정 주행 (속도: -100 ~ 100)"""
        try:
            self.robot.wheels(left_speed, right_speed)
            time.sleep(duration_sec)
            self.robot.stop()
        except Exception as e:
            print(f"[WARN] 주행 오류: {e}")

    def run_sorting_sequence(self, category: str):
        """
        ✨ 분리배출 핵심 수거 시퀀스
        6프레임 감지 ➔ 삐! ➔ 집게열고 4초 거치 대기 ➔ 집게닫기 ➔ 주행 ➔ 집게열기 ➔ 복귀
        """
        print(f"\n🤖 [{category}] 6프레임 감지 완료! 분리배출 자율 수거를 시작합니다.")
        self.beep(1)

        # 1. LED 점등
        leds = LED_MAP.get(category, ("off", "off"))
        self.set_led(leds[0], leds[1])

        # 2. 제자리 멈춰 집게 열기
        self.control_gripper("open")

        # 3. 4초간 쓰레기 거치 대기 카운트다운
        print(f"  ⏱️ 쓰레기를 집게 사이에 놓아주세요 ({WAIT_PLACEMENT_SEC}초 대기 중)...")
        for i in range(int(WAIT_PLACEMENT_SEC), 0, -1):
            print(f"    - 남은 시간: {i}초...")
            time.sleep(1.0)

        # 4. 집게 닫기 쓰레기 포획
        self.beep(1)
        self.control_gripper("close")

        # 5. 수거함 주행 (예시 전진 주행)
        print("  🚚 수거함 지정 위치로 주행 이동 중...")
        self.drive_wheels(35, 35, 1.5)

        # 6. 쓰레기 투입 (집게 열기)
        print("  🎉 수거함 도착! 쓰레기 투입 중...")
        self.control_gripper("open")
        time.sleep(0.5)

        # 7. 대칭 역주행 복귀 (오차 0.00cm)
        print("  ↩️ 원위치로 역주행 복귀 중...")
        self.drive_wheels(-35, -35, 1.5)

        # 8. 대기 상태 전환
        self.set_led("off", "off")
        self.control_gripper("open")
        print("  ✅ 시작 위치 복귀 완료!\n")


def main():
    print("=" * 65)
    print("  🐹 햄스터 로봇 AI 쓰레기 분리배출 개발자 스타터 템플릿")
    print("=" * 65)

    bot = HamsterBotController()

    try:
        # 스타터 데모 시퀀스 실행
        bot.run_sorting_sequence("플라스틱/페트병")
        bot.run_sorting_sequence("종이")
    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 중단되었습니다.")
    finally:
        bot.set_led("off", "off")
        bot.robot.stop()
        print("[INFO] 안전 종료 완료.")


if __name__ == "__main__":
    main()
