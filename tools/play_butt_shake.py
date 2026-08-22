"""
햄스터 로봇 '엉덩이 흔들기 댄스' (Wiggle Butt Dance) 쇼 스크립트
===================================================================
실행 방법:
    python tools/play_butt_shake.py
    또는
    uv run python tools/play_butt_shake.py
"""

import sys
import io
import time
from roboid import Hamster, wait

# Windows 콘솔에서 이모지 출력 시 CP949 인코딩 오류가 발생하는 것을 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def waddle_butt_dance():
    print("햄스터 로봇에 연결하는 중...")
    try:
        hamster = Hamster()
        wait(1000)  # 연결 대기
        print("연결 성공! 🕺")
    except Exception as e:
        print(f"햄스터 연결 실패: {e}")
        print("\n[!] BLE 동글이 PC에 연결되어 있고, 햄스터 로봇 전원이 켜져 있는지 확인하세요.")
        return

    print("\n" + "=" * 60)
    print("   🍑 햄스터 로봇의 '엉덩이 흔들기 댄스 쇼' 시작! 🍑")
    print("=" * 60)

    # 1단계: 준비 운동 (부저 삐빅 + LED 깜빡)
    print("📢 1단계: 준비 운동!")
    hamster.leds("magenta", "magenta")
    hamster.beep()
    wait(200)
    hamster.leds("off", "off")
    wait(100)
    hamster.beep()
    hamster.leds("cyan", "cyan")
    wait(500)
    hamster.leds("off", "off")

    # 2단계: 제자리 엉덩이 흔들기 (보통 속도)
    print("💃 2단계: 제자리 엉덩이 살랑살랑~")
    for i in range(8):
        sys.stdout.write(f"\r🍑 흔들흔들 (좌) [{'◀' if i%2==0 else '  '}]")
        sys.stdout.flush()
        hamster.leds("red", "off")
        hamster.wheels(-60, 60)
        wait(120)
        
        sys.stdout.write(f"\r🍑 흔들흔들 (우) [{'  ' if i%2==0 else '▶'}]")
        sys.stdout.flush()
        hamster.leds("off", "blue")
        hamster.wheels(60, -60)
        wait(120)

    hamster.stop()
    hamster.leds("off", "off")
    wait(300)

    # 3단계: 앞으로 가며 엉덩이 흔들기 (지그재그 주행)
    print("\n🚶 3단계: 앞으로 전진하며 흔들기!")
    for _ in range(4):
        sys.stdout.write("\r✨ 전진 흔들흔들 [◀]")
        sys.stdout.flush()
        hamster.leds("yellow", "off")
        hamster.wheels(30, 80)
        wait(200)
        
        sys.stdout.write("\r✨ 전진 흔들흔들 [▶]")
        sys.stdout.flush()
        hamster.leds("off", "yellow")
        hamster.wheels(80, 30)
        wait(200)

    hamster.stop()
    wait(300)

    # 4단계: 뒤로 가며 엉덩이 흔들기 (백 워킹 흔들기)
    print("\n🔙 4단계: 뒤로 후진하며 흔들기!")
    for _ in range(4):
        sys.stdout.write("\r✨ 후진 흔들흔들 [◀]")
        sys.stdout.flush()
        hamster.leds("cyan", "off")
        hamster.wheels(-20, -80)
        wait(200)
        
        sys.stdout.write("\r✨ 후진 흔들흔들 [▶]")
        sys.stdout.flush()
        hamster.leds("off", "cyan")
        hamster.wheels(-80, -20)
        wait(200)

    hamster.stop()
    wait(300)

    # 5단계: 대망의 피날레 - 초고속 광속 엉덩이 흔들기!
    print("\n🔥 5단계: 광속 엉덩이 흔들기 피날레!!!")
    for i in range(12):
        # 짝수번은 왼쪽 점등, 홀수번은 오른쪽 점등
        if i % 2 == 0:
            hamster.leds("magenta", "off")
            hamster.wheels(-100, 100)
            sys.stdout.write("\r🍑 [광속] ◀◀◀ 🍑")
        else:
            hamster.leds("off", "magenta")
            hamster.wheels(100, -100)
            sys.stdout.write("\r🍑 [광속] ▶▶▶ 🍑")
        sys.stdout.flush()
        wait(80)

    # 종료 및 정지
    hamster.stop()
    hamster.leds("green", "green")
    hamster.beep()
    print("\n\n🎉 댄스 쇼 종료! 감사합니다! 👏👏👏")
    wait(1000)
    hamster.leds("off", "off")

if __name__ == "__main__":
    waddle_butt_dance()
