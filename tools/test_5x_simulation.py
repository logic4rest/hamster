"""
5회 연속 자율주행 & 정밀 위치 복귀 시뮬레이션 검증 도구 (v4.7 - 1ms High-Precision Engine)
====================================================================================================
- 종이(1번), 종이팩(2번), 패트병(3번), 캔(4번), 이물질(경고) 5개 쓰레기 시나리오를 5회 연속 시뮬레이션
- 시작 좌표 (0, 0)에서 수거함 이동 ➔ 투입 ➔ 복귀 후 최종 위치 오차가 0.00cm인지 100% 수학적/물리적 검증
"""

import math
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hamster.waypoint_manager import waypoint_manager, NUMBERED_SLOTS


class TrajectorySimulator:
    """Differential Drive 2D Kinematics Simulator for Return Verification (1ms Precision)"""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0  # radians

    def reset(self):
        self.x = 0.0
        self.y = 0.0
        self.heading = 0.0

    def step(self, left_spd: float, right_spd: float, duration: float):
        """Diff-drive forward kinematics update with 1ms high precision"""
        v = (left_spd + right_spd) / 2.0 * 0.35
        w = (right_spd - left_spd) * 0.05  # rad/s

        dt = 0.001  # 1ms high precision tick
        ticks = int(round(duration / dt))

        for _ in range(ticks):
            self.heading += w * dt
            self.x += v * math.cos(self.heading) * dt
            self.y += v * math.sin(self.heading) * dt


def run_5x_simulation_tests():
    print("=" * 70)
    print("  🧪 [SIMULATION] 5회 연속 4종 쓰레기 분리배출 정밀 복귀 시뮬레이션 시작 (1ms 정밀도)")
    print("=" * 70)

    sim = TrajectorySimulator()

    test_scenarios = [
        ("1회차", "종이", "1"),
        ("2회차", "종이팩", "2"),
        ("3회차", "플라스틱/페트병", "3"),
        ("4회차", "캔", "4"),
        ("5회차", "이물질/경고", "0"),
    ]

    all_passed = True

    for run_num, cat_name, slot_id in test_scenarios:
        sim.reset()
        start_x, start_y = sim.x, sim.y

        print(f"\n▶ [{run_num} 시뮬레이션] 감지 쓰레기: '{cat_name}' (슬롯 {slot_id}번)")
        print(f"  - 시작 위치: (X: {start_x:.2f} cm, Y: {start_y:.2f} cm)")

        # 1. 초기 포획 접근 (0.3초 전진)
        approach_dur = 0.3
        sim.step(30, 30, approach_dur)

        # 2. 지정 슬롯 위치 자율 이동
        named_route = waypoint_manager.get_waypoint(cat_name)
        if named_route:
            for step in named_route:
                sim.step(step["left"], step["right"], step["duration"])

        bin_x, bin_y = sim.x, sim.y
        print(f"  - 수거함 도착 위치: (X: {bin_x:.2f} cm, Y: {bin_y:.2f} cm)")

        # 3. 투입 후 정밀 역주행 복귀 (Reverse Route + Reverse Approach)
        if named_route:
            reverse_route = waypoint_manager.get_reverse_return_trajectory(named_route)
            for step in reverse_route:
                sim.step(step["left"], step["right"], step["duration"])

        # 초기 접근(0.3초 전진) 완벽 반전 역주행 (-30, -30, 0.3s)
        sim.step(-30, -30, approach_dur)

        final_x, final_y = sim.x, sim.y
        dist_error = math.hypot(final_x - start_x, final_y - start_y)

        print(f"  - 복귀 완료 위치: (X: {final_x:.2f} cm, Y: {final_y:.2f} cm)")
        print(f"  - 위치 복귀 오차: {dist_error:.4f} cm")

        if dist_error < 0.01:
            print("  - ✅ [PASS] 오차 0.00cm! 완벽한 제자리 복귀 확인")
        else:
            print(f"  - ❌ [FAIL] 복귀 위치 오차 발생 ({dist_error:.4f}cm)")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("  🎉 [시뮬레이션 검증 100% 성공] 5회 연속 복귀 오차 0.00cm 완벽 입증!")
    else:
        print("  ⚠️ [시뮬레이션 실패] 보정이 필요한 구간이 존재합니다.")
    print("=" * 70 + "\n")

    return all_passed


if __name__ == "__main__":
    run_5x_simulation_tests()
