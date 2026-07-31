"""
햄스터 로봇 가속도 센서 고장 진단 도구
======================================
소리/LED 없이 순수하게 센서 원시값만 5초간 수집하여
센서가 정상인지, 고장인지, 노이즈가 심한지 자동 판정합니다.

실행 방법:
    cd hamster
    uv run python tools/diagnose_accel.py
"""

import sys
import time
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("\n" + "=" * 60)
    print("  [햄스터 봇 가속도 센서 고장 진단 도구]")
    print("=" * 60)
    print("  >>> 소리/LED 변경 없이 센서 원시값만 읽습니다 <<<")
    print("  >>> 로봇을 바닥에 가만히 놓아 주세요! <<<\n")

    try:
        from roboid import Hamster
    except ImportError:
        print("[오류] roboid 라이브러리 없음")
        sys.exit(1)

    print("[INFO] 로봇 연결 중...")
    hamster = Hamster()
    time.sleep(2.0)
    print("[OK] 연결 완료!\n")

    # ── 5초간 원시값 수집 (소리/LED 조작 없음) ──
    print("[진단] 5초간 가속도 센서 원시값을 수집합니다... 로봇을 만지지 마세요!")
    print("-" * 60)

    samples_x = []
    samples_y = []
    samples_z = []

    duration = 5.0
    start = time.time()
    count = 0

    while time.time() - start < duration:
        ax = hamster.acceleration_x()
        ay = hamster.acceleration_y()
        az = hamster.acceleration_z()
        samples_x.append(ax)
        samples_y.append(ay)
        samples_z.append(az)
        count += 1

        # 매 0.5초마다 현재값 출력
        if count % 10 == 0:
            elapsed = time.time() - start
            print(f"  [{elapsed:.1f}s] X={ax:>5d}  Y={ay:>5d}  Z={az:>5d}")

        time.sleep(0.05)

    print("-" * 60)
    print(f"\n[결과] 총 {count}개 샘플 수집 완료\n")

    # ── 통계 분석 ──
    def stats(name, data):
        avg = sum(data) / len(data)
        mn = min(data)
        mx = max(data)
        rng = mx - mn
        variance = sum((v - avg)**2 for v in data) / len(data)
        std = math.sqrt(variance)
        return avg, mn, mx, rng, std

    print(f"  {'축':^4} | {'평균':^8} | {'최소':^8} | {'최대':^8} | {'범위(변동폭)':^12} | {'표준편차':^8}")
    print("  " + "-" * 58)

    results = {}
    for name, data in [("X", samples_x), ("Y", samples_y), ("Z", samples_z)]:
        avg, mn, mx, rng, std = stats(name, data)
        results[name] = {"avg": avg, "min": mn, "max": mx, "range": rng, "std": std}
        print(f"  {name:^4} | {avg:>8.1f} | {mn:>8d} | {mx:>8d} | {rng:>12d} | {std:>8.1f}")

    # ── 판정 ──
    print("\n" + "=" * 60)
    print("  [자동 판정 결과]")
    print("=" * 60)

    issues = []

    # 1. 센서가 항상 0인 경우 -> 센서 고장 의심
    all_zero = all(v == 0 for v in samples_x) and all(v == 0 for v in samples_y) and all(v == 0 for v in samples_z)
    if all_zero:
        issues.append("  [고장 의심] 모든 축 값이 0 입니다. 센서가 응답하지 않습니다.")

    # 2. 노이즈 범위가 비정상적으로 큰 경우 (정지 상태에서 range > 30)
    for name in ["X", "Y", "Z"]:
        r = results[name]
        if r["range"] > 30:
            issues.append(f"  [노이즈 과다] {name}축 변동폭={r['range']} (정상: 10 이하). 센서 불안정 또는 로봇이 움직였습니다.")
        elif r["range"] > 15:
            issues.append(f"  [노이즈 주의] {name}축 변동폭={r['range']} (양호: 10 이하). 약간 높지만 사용 가능합니다.")

    # 3. Z축 중력 확인 (바르게 놓으면 Z 방향에 중력이 있어야 함)
    z_avg = results["Z"]["avg"]
    x_avg = results["X"]["avg"]
    y_avg = results["Y"]["avg"]
    gravity_magnitude = math.sqrt(x_avg**2 + y_avg**2 + z_avg**2)

    if gravity_magnitude < 5:
        issues.append(f"  [고장 의심] 중력 벡터 합산={gravity_magnitude:.1f} (너무 작음). 센서가 중력을 감지하지 못합니다.")

    if len(issues) == 0:
        print("\n  >>> 센서 정상! <<<")
        print(f"  중력 벡터 합산: {gravity_magnitude:.1f}")
        print(f"  Z축 평균: {z_avg:.1f} (바르게 놓인 상태의 중력 기준값)")
        print(f"  X/Y축 평균: X={x_avg:.1f}, Y={y_avg:.1f} (평평하면 0 근처)")
        print(f"\n  이 로봇에 최적화된 충격 임계값 권장: {max(int(results['X']['range'] + results['Y']['range'] + results['Z']['range']) * 3, 60)}")
    else:
        print()
        for issue in issues:
            print(issue)

    # 최적 임계값 계산
    noise_floor = max(results["X"]["range"], results["Y"]["range"], results["Z"]["range"])
    recommended_threshold = max(int(noise_floor * 4), 60)
    print(f"\n  [참고] 현재 센서 노이즈 최대 변동폭: {noise_floor}")
    print(f"  [참고] 권장 충격 감지 임계값: {recommended_threshold} (현재 설정: 50)")

    if recommended_threshold > 50:
        print(f"\n  !!! 현재 임계값(50)이 센서 노이즈({noise_floor})보다 낮아서")
        print(f"      가만히 있어도 소리가 날 수 있습니다!")
        print(f"      임계값을 {recommended_threshold} 이상으로 높여야 합니다.")

    print("\n" + "=" * 60 + "\n")

    hamster.stop()

if __name__ == "__main__":
    main()
