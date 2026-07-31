"""
Hamster Bot Smart Autonomous Driving Launcher
================================================
실행 방법:
    python tools/autonomous_drive.py
    uv run python tools/autonomous_drive.py
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hamster.dashboard import launch_dashboard

if __name__ == "__main__":
    print("=" * 60)
    print("  [햄스터 봇 스마트 자율주행 & 센서 융합 시스템]")
    print("  - 내장 바닥 센서(IR) 기반 PID 곡선 추종 라인 트레이싱")
    print("  - 전방 근접 센서(IR) 기반 장애물 자동 탐지 및 우회 주행")
    print("  - 정지선/교차로 감지 및 비상등/멜로디 자율 주차 시퀀스")
    print("  - 3축 가속도 센서 기반 충돌/뒤집힘 급정지 안전 Guard")
    print("  - Pygame 실시간 대시보드 UI (TAB키로 자율/수동 모드 전환)")
    print("=" * 60)
    launch_dashboard()
