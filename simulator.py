"""
AI 햄스터 로봇 분리배출 스마트 시뮬레이터 (v4.3 유리병 제거 & 4종 쓰레기 분리배출 최적화 에디션)
====================================================================================================
- 유리병 카테고리 완전히 제거 (플라스틱/페트병으로 통합)
- roboid 공식 open_gripper(), close_gripper(), release_gripper() API 동기화
- 실물 로봇이나 카메라 없이도 쓰레기 분리배출 및 집게 운반 모션을 100% 2D 그래픽 시뮬레이션
- 4종 지정 수거함 (종이/종이팩/플라스틱(페트병)/캔) 및 경고 오배출 모션 지원

실행 방법:
    python simulator.py
    uv run python simulator.py
"""

import json
import math
import os
import sys
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

# ── 설정 및 경로 ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
STATS_PATH   = PROJECT_ROOT / "stats.json"

# 로봇 하드웨어 로드 시도
ROBOT_AVAILABLE = False
try:
    from roboid import Hamster
    ROBOT_AVAILABLE = True
except Exception:
    pass

# 색상 파스텔 테마
BG_COLOR       = "#1E1E2E"
PANEL_COLOR    = "#2B2B3D"
TEXT_COLOR     = "#FFFFFF"
ACCENT_COLOR   = "#7952B3"

BIN_COLORS = {
    "플라스틱/페트병": "#007ACC",     # 파란색
    "캔": "#28A745",                 # 초록색
    "종이": "#FFC107",               # 노란색
    "종이팩": "#17A2B8",              # 하늘색
    "이물질/경고": "#DC3545",         # 빨간색
}


class HamsterSimulatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🐹 AI 쓰레기 4종 분리배출 햄스터 로봇 시뮬레이터 v4.3")
        self.root.geometry("1024x720")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        # 상태 변수
        self.hamster_robot = None
        self.is_connected = False
        self.is_animating = False
        self.stats = self.load_stats()

        # 로봇 2D 시뮬레이션 위치 (캔버스 중앙)
        self.home_x = 450
        self.home_y = 300
        self.robot_x = self.home_x
        self.robot_y = self.home_y
        self.robot_angle = 0.0          # 라디안 (0: 우측, -pi/2: 상단)
        self.gripper_open = True
        self.left_led = "OFF"
        self.right_led = "OFF"

        self.setup_ui()
        self.reset_robot_position()
        self.draw_canvas()

    def load_stats(self) -> dict:
        default_stats = {
            "플라스틱/페트병": 0,
            "캔": 0,
            "종이": 0,
            "종이팩": 0,
            "이물질/경고": 0,
            "total": 0,
        }
        if STATS_PATH.exists():
            try:
                with open(STATS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "유리병(별도 수거)" in data:
                        data["플라스틱/페트병"] = data.get("플라스틱/페트병", 0) + data.pop("유리병(별도 수거)")
                    default_stats.update(data)
            except Exception:
                pass
        return default_stats

    def save_stats(self):
        try:
            with open(STATS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def setup_ui(self):
        # 1. 상단 타이틀 & 헤더
        header_frame = tk.Frame(self.root, bg=PANEL_COLOR, height=60)
        header_frame.pack(side=tk.TOP, fill=tk.X)

        lbl_title = tk.Label(
            header_frame,
            text="🐹 햄스터 로봇 스마트 4종 분리배출 2D 시뮬레이터 (유리병 제거 최적화)",
            font=("맑은 고딕", 16, "bold"),
            bg=PANEL_COLOR,
            fg="#F8F8F2",
        )
        lbl_title.pack(side=tk.LEFT, padx=20, pady=15)

        self.btn_connect = tk.Button(
            header_frame,
            text="🔌 실제 로봇 연결",
            font=("맑은 고딕", 11, "bold"),
            bg="#007ACC",
            fg="white",
            activebackground="#005999",
            activeforeground="white",
            relief=tk.FLAT,
            padx=15,
            pady=5,
            command=self.toggle_robot_connection,
        )
        self.btn_connect.pack(side=tk.RIGHT, padx=20, pady=12)

        # 2. 메인 프레임 (좌: 컨트롤 & HUD, 우: 2D 그래픽 캔버스)
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # ── 좌측 컨트롤 패널 ──────────────────────────────────────────────────
        left_panel = tk.Frame(main_frame, bg=PANEL_COLOR, width=320)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_panel.pack_propagate(False)

        # 쓰레기 분류 테스트 버튼 섹션
        lbl_sec1 = tk.Label(
            left_panel,
            text="🗑️ 쓰레기 4종 분리배출 테스트",
            font=("맑은 고딕", 13, "bold"),
            bg=PANEL_COLOR,
            fg="#F8F8F2",
        )
        lbl_sec1.pack(anchor="w", padx=15, pady=(15, 10))

        buttons = [
            ("📄 [1번] 종이 수거함 이동 (노란색)", "종이", "#FFC107", "black"),
            ("🩵 [2번] 종이팩 수거함 이동 (하늘색)", "종이팩", "#17A2B8", "white"),
            ("🥤 [3번] 패트병(플라스틱) 수거함 이동 (파란색)", "플라스틱/페트병", "#007ACC", "white"),
            ("🥫 [4번] 캔 수거함 이동 (초록색)", "캔", "#28A745", "white"),
            ("🚨 오배출/이물질 경고 동작 (빨간색)", "이물질/경고", "#DC3545", "white"),
        ]

        for text, cat, bg, fg in buttons:
            btn = tk.Button(
                left_panel,
                text=text,
                font=("맑은 고딕", 11, "bold"),
                bg=bg,
                fg=fg,
                activebackground=bg,
                relief=tk.RAISED,
                bd=2,
                pady=8,
                command=lambda c=cat: self.trigger_sorting_motion(c),
            )
            btn.pack(fill=tk.X, padx=15, pady=5)

        # 실물 집게 수동 테스트 버튼
        lbl_sec2 = tk.Label(
            left_panel,
            text="🦾 roboid 공식 집게 수동 제어",
            font=("맑은 고딕", 13, "bold"),
            bg=PANEL_COLOR,
            fg="#F8F8F2",
        )
        lbl_sec2.pack(anchor="w", padx=15, pady=(20, 10))

        grp_frame = tk.Frame(left_panel, bg=PANEL_COLOR)
        grp_frame.pack(fill=tk.X, padx=15)

        btn_open = tk.Button(
            grp_frame,
            text="👐 open_gripper()",
            font=("맑은 고딕", 10, "bold"),
            bg="#6c757d",
            fg="white",
            pady=6,
            command=self.manual_open_gripper,
        )
        btn_open.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        btn_close = tk.Button(
            grp_frame,
            text="✊ close_gripper()",
            font=("맑은 고딕", 10, "bold"),
            bg="#28A745",
            fg="white",
            pady=6,
            command=self.manual_close_gripper,
        )
        btn_close.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # 통계 현황 HUD
        lbl_sec3 = tk.Label(
            left_panel,
            text="📊 실시간 배출 통계 현황",
            font=("맑은 고딕", 13, "bold"),
            bg=PANEL_COLOR,
            fg="#F8F8F2",
        )
        lbl_sec3.pack(anchor="w", padx=15, pady=(20, 10))

        self.lbl_stats = tk.Label(
            left_panel,
            text=self.get_stats_text(),
            font=("맑은 고딕", 10),
            bg="#1E1E2E",
            fg="#A6ACCD",
            justify=tk.LEFT,
            anchor="w",
            padx=12,
            pady=12,
            relief=tk.SUNKEN,
        )
        self.lbl_stats.pack(fill=tk.X, padx=15)

        # ── 우측 2D 그래픽 캔버스 ──────────────────────────────────────────────
        right_panel = tk.Frame(main_frame, bg=PANEL_COLOR)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            right_panel,
            bg="#11111B",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 하단 상태 바
        self.lbl_status_msg = tk.Label(
            right_panel,
            text="🟢 시뮬레이터 준비 완료. 버튼을 눌러 테스트하세요.",
            font=("맑은 고딕", 11),
            bg=PANEL_COLOR,
            fg="#89DDFF",
            anchor="w",
            padx=15,
            pady=8,
        )
        self.lbl_status_msg.pack(fill=tk.X)

    def get_stats_text(self) -> str:
        s = self.stats
        return (
            f"📄 종이: {s.get('종이', 0)}개\n"
            f"🩵 종이팩: {s.get('종이팩', 0)}개\n"
            f"🥤 플라스틱/페트병: {s.get('플라스틱/페트병', 0)}개\n"
            f"🥫 캔: {s.get('캔', 0)}개\n"
            f"🚨 오배출/경고: {s.get('이물질/경고', 0)}개\n"
            f"───────────────────\n"
            f"🏆 총 분리배출 횟수: {s.get('total', 0)}회"
        )

    def update_stats_ui(self):
        self.lbl_stats.config(text=self.get_stats_text())

    def set_status(self, msg: str):
        self.lbl_status_msg.config(text=msg)

    def toggle_robot_connection(self):
        if not ROBOT_AVAILABLE:
            messagebox.showerror("오류", "roboid 모듈이 설치되어 있지 않습니다.\n실물 연결 없이 2D 그래픽 모드로 동작합니다.")
            return

        if not self.is_connected:
            try:
                self.hamster_robot = Hamster()
                self.is_connected = True
                self.btn_connect.config(text="🟢 연결됨 (해제)", bg="#28A745")
                self.set_status("✅ 햄스터 실물 로봇 연결 성공! 시뮬레이터와 동기화됩니다.")
            except Exception as e:
                messagebox.showerror("연결 실패", f"햄스터 로봇 연결 중 오류 발생:\n{e}")
        else:
            try:
                if self.hamster_robot:
                    self.hamster_robot.stop()
                    self.hamster_robot.leds("off", "off")
            except Exception:
                pass
            self.hamster_robot = None
            self.is_connected = False
            self.btn_connect.config(text="🔌 실제 로봇 연결", bg="#007ACC")
            self.set_status("🔌 실물 로봇 연결이 해제되었습니다.")

    def manual_open_gripper(self):
        self.gripper_open = True
        if self.is_connected and self.hamster_robot:
            try:
                if hasattr(self.hamster_robot, "open_gripper"):
                    self.hamster_robot.open_gripper()
            except Exception:
                pass
        self.set_status("🦾 [집게 제어] open_gripper() 실행 - 집게가 열렸습니다.")
        self.draw_canvas()

    def manual_close_gripper(self):
        self.gripper_open = False
        if self.is_connected and self.hamster_robot:
            try:
                if hasattr(self.hamster_robot, "close_gripper"):
                    self.hamster_robot.close_gripper()
            except Exception:
                pass
        self.set_status("🦾 [집게 제어] close_gripper() 실행 - 집게가 닫혔습니다.")
        self.draw_canvas()

    def reset_robot_position(self):
        self.robot_x = self.home_x
        self.robot_y = self.home_y
        self.robot_angle = -math.pi / 2  # 위쪽 바라보기
        self.left_led = "OFF"
        self.right_led = "OFF"

    def draw_canvas(self):
        self.canvas.delete("all")

        # 1. 분리수거함 4종 그리드 렌더링
        bins_data = [
            ("종이", 100, 80, BIN_COLORS["종이"], "📄 1번 종이"),
            ("종이팩", 280, 80, BIN_COLORS["종이팩"], "🩵 2번 종이팩"),
            ("플라스틱/페트병", 460, 80, BIN_COLORS["플라스틱/페트병"], "🥤 3번 패트병"),
            ("캔", 640, 80, BIN_COLORS["캔"], "🥫 4번 캔"),
        ]

        for cat, x, y, color, label in bins_data:
            self.canvas.create_rectangle(x, y, x + 110, y + 90, fill=color, outline="white", width=2)
            self.canvas.create_text(x + 55, y + 45, text=label, fill="white", font=("맑은 고딕", 10, "bold"))

        # 2. 시작 베이스 마크
        self.canvas.create_oval(self.home_x - 30, self.home_y - 30, self.home_x + 30, self.home_y + 30, outline="#555577", width=2, dash=(4, 4))
        self.canvas.create_text(self.home_x, self.home_y + 42, text="🏠 시작 위치", fill="#8888AA", font=("맑은 고딕", 9))

        # 3. 햄스터 로봇 차체 (2D 오벌)
        rx, ry = self.robot_x, self.robot_y
        size = 28
        cos_a = math.cos(self.robot_angle)
        sin_a = math.sin(self.robot_angle)

        self.canvas.create_oval(rx - size, ry - size, rx + size, ry + size, fill="#E6E6E6", outline="#333333", width=3)

        # 4. 좌우 LED 표시
        l_x = rx + (size * 0.7) * cos_a - (size * 0.5) * sin_a
        l_y = ry + (size * 0.7) * sin_a + (size * 0.5) * cos_a
        r_x = rx + (size * 0.7) * cos_a + (size * 0.5) * sin_a
        r_y = ry + (size * 0.7) * sin_a - (size * 0.5) * cos_a

        l_color = self.get_led_color(self.left_led)
        r_color = self.get_led_color(self.right_led)

        self.canvas.create_oval(l_x - 5, l_y - 5, l_x + 5, l_y + 5, fill=l_color, outline="black")
        self.canvas.create_oval(r_x - 5, r_y - 5, r_x + 5, r_y + 5, fill=r_color, outline="black")

        # 5. roboid 공식 실물 집게 (Gripper Arms) 렌더링
        g_len = 24
        front_x = rx + size * cos_a
        front_y = ry + size * sin_a

        grip_angle_offset = 0.45 if self.gripper_open else 0.12

        g1_angle = self.robot_angle - grip_angle_offset
        g2_angle = self.robot_angle + grip_angle_offset

        g1_end_x = front_x + g_len * math.cos(g1_angle)
        g1_end_y = front_y + g_len * math.sin(g1_angle)
        g2_end_x = front_x + g_len * math.cos(g2_angle)
        g2_end_y = front_y + g_len * math.sin(g2_angle)

        g_color = "#28A745" if not self.gripper_open else "#FFC107"
        self.canvas.create_line(front_x, front_y, g1_end_x, g1_end_y, fill=g_color, width=4, capstyle=tk.ROUND)
        self.canvas.create_line(front_x, front_y, g2_end_x, g2_end_y, fill=g_color, width=4, capstyle=tk.ROUND)

    def get_led_color(self, led_val) -> str:
        if led_val == "blue":
            return "#007ACC"
        elif led_val == "green":
            return "#28A745"
        elif led_val == "yellow":
            return "#FFC107"
        elif led_val == "cyan":
            return "#17A2B8"
        elif led_val == "red":
            return "#DC3545"
        return "#444444"

    def trigger_sorting_motion(self, category: str):
        if self.is_animating:
            return
        self.is_animating = True
        threading.Thread(target=self.run_sorting_sequence, args=(category,), daemon=True).start()

    def run_sorting_sequence(self, category: str):
        self.set_status(f"🚀 [{category}] 확정 시퀀스 시작 - 집게 열기 및 접근")

        # LED 켜기
        led_color = "yellow"
        if category == "플라스틱/페트병":
            led_color = "blue"
        elif category == "캔":
            led_color = "green"
        elif category == "종이팩":
            led_color = "cyan"
        elif category == "이물질/경고":
            led_color = "red"

        self.left_led = led_color
        self.right_led = led_color

        if self.is_connected and self.hamster_robot:
            try:
                self.hamster_robot.leds(led_color, led_color)
                self.hamster_robot.beep()
            except Exception:
                pass

        # 1. 집게 열기
        self.gripper_open = True
        if self.is_connected and self.hamster_robot:
            try:
                if hasattr(self.hamster_robot, "open_gripper"):
                    self.hamster_robot.open_gripper()
            except Exception:
                pass
        self.draw_canvas()
        time.sleep(0.5)

        # 2. 집게 닫기 (쓰레기 포획)
        self.set_status(f"✊ [{category}] 쓰레기 포획 완료! close_gripper()")
        self.gripper_open = False
        if self.is_connected and self.hamster_robot:
            try:
                if hasattr(self.hamster_robot, "close_gripper"):
                    self.hamster_robot.close_gripper()
            except Exception:
                pass
        self.draw_canvas()
        time.sleep(0.6)

        # 3. 해당 수거함으로 이동 애니메이션
        target_positions = {
            "종이": (155, 180, -math.pi / 2),
            "종이팩": (335, 180, -math.pi / 2),
            "플라스틱/페트병": (515, 180, -math.pi / 2),
            "캔": (695, 180, -math.pi / 2),
            "이물질/경고": (self.home_x, self.home_y + 100, math.pi / 2),
        }

        target_x, target_y, target_a = target_positions.get(category, (self.home_x, self.home_y, -math.pi / 2))

        self.set_status(f"🚚 [{category}] 수거함 위치로 이동 중...")

        if self.is_connected and self.hamster_robot:
            try:
                self.hamster_robot.wheels(35, 35)
            except Exception:
                pass

        steps = 25
        dx = (target_x - self.robot_x) / steps
        dy = (target_y - self.robot_y) / steps

        for _ in range(steps):
            self.robot_x += dx
            self.robot_y += dy
            self.robot_angle = target_a
            self.draw_canvas()
            time.sleep(0.04)

        if self.is_connected and self.hamster_robot:
            try:
                self.hamster_robot.stop()
            except Exception:
                pass

        time.sleep(0.4)

        # 4. 집게 해제 (투입)
        self.set_status(f"👐 [{category}] 수거함 투입 완료! release_gripper()")
        self.gripper_open = True
        if self.is_connected and self.hamster_robot:
            try:
                if hasattr(self.hamster_robot, "release_gripper"):
                    self.hamster_robot.release_gripper()
            except Exception:
                pass
        self.draw_canvas()
        time.sleep(0.6)

        # 5. 복귀 애니메이션
        self.set_status(f"↩️ [{category}] 복귀 중...")

        if self.is_connected and self.hamster_robot:
            try:
                self.hamster_robot.wheels(-35, -35)
            except Exception:
                pass

        for _ in range(steps):
            self.robot_x -= dx
            self.robot_y -= dy
            self.draw_canvas()
            time.sleep(0.04)

        if self.is_connected and self.hamster_robot:
            try:
                self.hamster_robot.stop()
                self.hamster_robot.leds("off", "off")
            except Exception:
                pass

        self.reset_robot_position()
        self.draw_canvas()

        # 통계 카운트 증가
        self.stats[category] = self.stats.get(category, 0) + 1
        self.stats["total"] += 1
        self.save_stats()
        self.update_stats_ui()

        self.set_status(f"✅ [{category}] 분리배출 완료 및 제자리 복귀!")
        self.is_animating = False


def main():
    root = tk.Tk()
    app = HamsterSimulatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
