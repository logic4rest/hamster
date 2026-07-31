"""
햄스터 로봇 가속도 센서(3축 Accelerometer) 실시간 진단 & 테스트 도구
==================================================================
개체별 센서 축 방향과 부호 상관없이 100% 정확한 뒤집힘 & 충격 테스트.

실행 방법:
    python tools/test_accelerometer.py
    uv run python tools/test_accelerometer.py
"""

import sys
import time
import math
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("\n" + "=" * 65)
    print("      [햄스터 봇 가속도 센서(동적 가속도 & 뒤집힘) 정밀 테스트]")
    print("=" * 65)
    print("  - 가만히 있을 때는 소리가 나지 않으며, 센서 방향을 자동 교정합니다.")
    print("  - 로봇을 실제로 톡 치거나 뒤집을 때만 경고음이 납니다.")
    print("  - [Ctrl+C]를 누르면 종료됩니다.\n")

    try:
        from roboid import Hamster
    except ImportError:
        print("[오류] roboid 라이브러리를 찾을 수 없습니다.")
        sys.exit(1)

    print("[INFO] 햄스터 로봇 연결 중...")
    hamster = Hamster()
    time.sleep(1.5)
    print("[OK] 연결 완료! 1초간 정위치 영점(Baseline)을 측정합니다...")

    # Initial baseline sampling (1 second)
    sample_x, sample_y, sample_z = [], [], []
    for _ in range(20):
        sample_x.append(hamster.acceleration_x())
        sample_y.append(hamster.acceleration_y())
        sample_z.append(hamster.acceleration_z())
        time.sleep(0.05)

    base_x = sum(sample_x) / len(sample_x)
    base_y = sum(sample_y) / len(sample_y)
    base_z = sum(sample_z) / len(sample_z)

    print(f"[OK] 영점 설정 완료 (Base X:{base_x:.1f}, Y:{base_y:.1f}, Z:{base_z:.1f})\n")

    print("-" * 70)
    print(f"{'Acc X':^8} | {'Acc Y':^8} | {'Acc Z':^8} | {'동적변화량(dA)':^14} | {'상태':^16}")
    print("-" * 70)

    try:
        while True:
            ax = hamster.acceleration_x()
            ay = hamster.acceleration_y()
            az = hamster.acceleration_z()

            # Dynamic Acceleration Delta (subtracting baseline)
            dx = ax - base_x
            dy = ay - base_y
            dz = az - base_z
            delta_acc = math.sqrt(dx**2 + dy**2 + dz**2)

            status_text = "정지 (정상)"
            led_l, led_r = "green", "green"

            # Check if robot is TRULY flipped upside down (Z axis sign inverted)
            is_flipped = (az * base_z < -100) or (base_z > 0 and az < -15) or (base_z < 0 and az > 15)

            # 1. 외부 충격 / 급가속 감지 (delta_acc > 50)
            if delta_acc > 50:
                status_text = "[충격!] IMPACT"
                led_l, led_r = "red", "red"
                try:
                    hamster.beep()
                except Exception:
                    pass

            # 2. 진짜 뒤집힘 감지
            elif is_flipped:
                status_text = "[뒤집힘] FLIP"
                led_l, led_r = "yellow", "yellow"
                try:
                    hamster.beep()
                except Exception:
                    pass

            # 3. 기울어짐 감지 (Abs delta > 25)
            elif abs(dx) > 25 or abs(dy) > 25:
                status_text = "[기울어짐] TILT"
                led_l, led_r = "blue", "blue"

            try:
                hamster.leds(led_l, led_r)
            except Exception:
                pass

            out_str = f"{ax:^8d} | {ay:^8d} | {az:^8d} | {delta_acc:^14.1f} | {status_text}"
            print(f"\r  {out_str}", end="", flush=True)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\n[INFO] 테스트 중지됨")
    finally:
        try:
            hamster.leds("off", "off")
            hamster.stop()
        except Exception:
            pass

if __name__ == "__main__":
    main()
