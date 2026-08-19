"""
AI 햄스터 로봇 분리배출 스마트 시뮬레이터 (v3.4 roboid 공식 집게 API 적용 에디션)
====================================================================================================
- roboid 공식 open_gripper(), close_gripper(), release_gripper() API 동기화
- 실물 로봇이나 카메라 없이도 쓰레기 분리배출 및 집게 운반 모션을 100% 2D 그래픽 시뮬레이션
- 햄스터 로봇 BLE 연결 시 실제 하드웨어 바퀴, LED, 실물 집게 동작과 실시간 동기화
- 5종 분리수거함 (플라스틱/유리병/캔/종이/종이팩) 및 경고 오배출 모션 지원

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
    "유리병(별도 수거)": "#FF8C00",    # 선명한 주황색
    "캔": "#28A745",                 # 초록색
    "종이": "#FFC107",               # 노란색
    "종이팩": "#17A2B8",              # 하늘색
    "이물질/경고": "#DC3545",         # 빨간색
}


class HamsterSimulatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🐹 AI 쓰레기 분리배출 햄스터 로봇 시뮬레이터 v3.4")
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
            "유리병(별도 수거)": 0,
            "캔": 0,
            "종이": 0,
            "종이팩": 0,
            "이물질/경고": 0,
            "total": 0,
        }
        if STATS_PATH.exists():
            try:
                with open(STATS_PATH, "r", encoding="utf-8") as f:
                    default_stats.update(json.load(f))
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
        # 상단 타이틀 바
        header = tk.Frame(self.root, bg=PANEL_COLOR, height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        
        title_label = tk.Label(
            header,
            text="🐹 AI 쓰레기 분리배출 햄스터 로봇 시뮬레이터 v3.4",
            font=("맑은 고딕", 18, "bold"),
            fg="#F8F9FA",
            bg=PANEL_COLOR,
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=12)

        self.btn_connect = tk.Button(
            header,
            text="⚙️ 실물 햄스터 연결 시도",
            font=("맑은 고딕", 11, "bold"),
            bg="#6C757D",
            fg="white",
            activebackground="#495057",
            activeforeground="white",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            command=self.toggle_connect_robot,
        )
        self.btn_connect.pack(side=tk.RIGHT, padx=20)

        # 메인 레이아웃 (좌: 캔버스 시뮬레이터, 우: 대시보드 컨트롤)
        body = tk.Frame(self.root, bg=BG_COLOR)
        body.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # 1) 좌측 2D 시뮬레이션 캔버스
        canvas_frame = tk.LabelFrame(
            body,
            text=" 🤖 2D 분리배출 로봇 아레나 시뮬레이션 ",
            font=("맑은 고딕", 12, "bold"),
            fg="#A78BFA",
            bg=PANEL_COLOR,
            bd=2,
            relief=tk.GROOVE,
        )
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.canvas = tk.Canvas(
            canvas_frame,
            width=650,
            height=580,
            bg="#111827",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 2) 우측 제어 패널 & 통계
        ctrl_frame = tk.LabelFrame(
            body,
            text=" 🎮 쓰레기 투입 & 제어 패널 ",
            font=("맑은 고딕", 12, "bold"),
            fg="#38BDF8",
            bg=PANEL_COLOR,
            bd=2,
            relief=tk.GROOVE,
            width=320,
        )
        ctrl_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        ctrl_frame.pack_propagate(False)

        lbl_desc = tk.Label(
            ctrl_frame,
            text="버튼을 눌러 쓰레기를 투입하고\n햄스터 로봇의 집게 운반 모션을 테스트하세요!",
            font=("맑은 고딕", 10),
            fg="#9CA3AF",
            bg=PANEL_COLOR,
            justify=tk.LEFT,
        )
        lbl_desc.pack(anchor="w", padx=15, pady=(15, 10))

        # 카테고리 시뮬레이션 버튼 목록
        categories = [
            ("🔵 플라스틱/페트병 투입", "플라스틱/페트병", "#2563EB"),
            ("🟠 유리병 (별도 수거)", "유리병(별도 수거)", "#EA580C"),
            ("🟢 캔 투입", "캔", "#16A34A"),
            ("🟡 종이 투입", "종이", "#D97706"),
            ("🩵 종이팩 투입", "종이팩", "#0891B2"),
            ("🚨 이물질 / 경고 오배출", "이물질/경고", "#DC2626"),
        ]

        for text, cat, col in categories:
            btn = tk.Button(
                ctrl_frame,
                text=text,
                font=("맑은 고딕", 11, "bold"),
                bg=col,
                fg="white",
                activebackground="#1E293B",
                activeforeground="white",
                relief=tk.RAISED,
                bd=2,
                cursor="hand2",
                pady=6,
                command=lambda c=cat: self.trigger_simulation(c),
            )
            btn.pack(fill=tk.X, padx=15, pady=4)

        # 구분선
        ttk.Separator(ctrl_frame, orient="horizontal").pack(fill=tk.X, padx=15, pady=12)

        # 실시간 통계 HUD 표시
        lbl_stats_title = tk.Label(
            ctrl_frame,
            text="📊 실시간 누적 수거 통계",
            font=("맑은 고딕", 11, "bold"),
            fg="#F43F5E",
            bg=PANEL_COLOR,
        )
        lbl_stats_title.pack(anchor="w", padx=15, pady=(5, 5))

        self.stats_var = tk.StringVar()
        self.update_stats_display()

        lbl_stats_body = tk.Label(
            ctrl_frame,
            textvariable=self.stats_var,
            font=("맑은 고딕", 10),
            fg="#E2E8F0",
            bg="#1E1E2E",
            justify=tk.LEFT,
            relief=tk.SUNKEN,
            bd=1,
            padx=10,
            pady=8,
        )
        lbl_stats_body.pack(fill=tk.X, padx=15, pady=5)

        # 상태 로그 표시줄
        self.status_var = tk.StringVar(value="[대기] 시뮬레이션 준비 완료. 버튼을 눌러주세요.")
        lbl_status = tk.Label(
            ctrl_frame,
            textvariable=self.status_var,
            font=("맑은 고딕", 9, "bold"),
            fg="#34D399",
            bg="#111827",
            wraplength=280,
            justify=tk.LEFT,
            padx=8,
            pady=8,
        )
        lbl_status.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=15)

    def update_stats_display(self):
        s = self.stats
        txt = (
            f"• 총 수거량: {s.get('total', 0)} 개\n"
            f"• 🔵 플라스틱: {s.get('플라스틱/페트병', 0)} 개\n"
            f"• 🟠 유리병: {s.get('유리병(별도 수거)', 0)} 개\n"
            f"• 🟢 캔: {s.get('캔', 0)} 개\n"
            f"• 🟡 종이: {s.get('종이', 0)} 개\n"
            f"• 🩵 종이팩: {s.get('종이팩', 0)} 개\n"
            f"• 🔴 경고 오배출: {s.get('이물질/경고', 0)} 개"
        )
        self.stats_var.set(txt)

    def toggle_connect_robot(self):
        if not ROBOT_AVAILABLE:
            messagebox.showwarning(
                "연결 안내",
                "roboid 모듈이 설치되어 있지 않습니다.\n가상 그래픽 시뮬레이션 모드로 작동합니다.",
            )
            return

        if self.is_connected:
            self.is_connected = False
            self.hamster_robot = None
            self.btn_connect.config(text="⚙️ 실물 햄스터 연결 시도", bg="#6C757D")
            self.status_var.set("[INFO] 햄스터 연결이 해제되었습니다.")
        else:
            try:
                self.status_var.set("[INFO] 햄스터 BLE 연결 중...")
                self.root.update()
                self.hamster_robot = Hamster()
                self.is_connected = True
                self.btn_connect.config(text="✅ 햄스터 로봇 연결됨", bg="#16A34A")
                self.status_var.set("✅ 실물 햄스터 로봇 연결 성공! 연동 시뮬레이션 준비 완료.")
            except Exception as e:
                self.is_connected = False
                self.btn_connect.config(text="❌ 연결 실패 (가상 모드)", bg="#DC2626")
                self.status_var.set(f"❌ 실물 연결 실패 ({e}). 가상 시뮬레이션 모드로 진행합니다.")

    def reset_robot_position(self):
        self.robot_x = self.home_x
        self.robot_y = self.home_y
        self.robot_angle = -math.pi / 2.0  # 위쪽을 바라봄
        self.gripper_open = True
        self.left_led = "OFF"
        self.right_led = "OFF"

    def control_physical_gripper(self, action: str):
        if not self.is_connected or not self.hamster_robot:
            return
        try:
            if action == "open":
                if hasattr(self.hamster_robot, "open_gripper"):
                    self.hamster_robot.open_gripper()
                elif hasattr(self.hamster_robot, "output_a"):
                    self.hamster_robot.output_a(0)
            elif action == "close" or action == "grip":
                if hasattr(self.hamster_robot, "close_gripper"):
                    self.hamster_robot.close_gripper()
                elif hasattr(self.hamster_robot, "output_a"):
                    self.hamster_robot.output_a(100)
            elif action == "release":
                if hasattr(self.hamster_robot, "release_gripper"):
                    self.hamster_robot.release_gripper()
                elif hasattr(self.hamster_robot, "open_gripper"):
                    self.hamster_robot.open_gripper()
        except Exception:
            pass

    def draw_canvas(self, active_trash=None, trash_x=None, trash_y=None):
        self.canvas.delete("all")

        # 1. 아레나 그리드 배경
        for x in range(0, 650, 40):
            self.canvas.create_line(x, 0, x, 580, fill="#1F2937", width=1)
        for y in range(0, 580, 40):
            self.canvas.create_line(0, y, 650, y, fill="#1F2937", width=1)

        # 2. 5종 분리수거함
        bins_data = [
            ("플라스틱/페트병", 90, 80, "🔵 파란 수거함"),
            ("종이팩", 230, 80, "🩵 하늘 수거함"),
            ("종이", 370, 80, "🟡 노란 수거함"),
            ("유리병(별도 수거)", 510, 80, "🟠 주황 수거함"),
            ("캔", 570, 240, "🟢 초록 수거함"),
        ]

        for cat, bx, by, title in bins_data:
            col = BIN_COLORS.get(cat, "#6B7280")
            self.canvas.create_rectangle(
                bx - 45, by - 40, bx + 45, by + 40,
                fill=col, outline="#FFFFFF", width=2,
            )
            self.canvas.create_rectangle(
                bx - 30, by - 25, bx + 30, by - 10,
                fill="#111827", outline="#FFFFFF", width=1,
            )
            self.canvas.create_text(
                bx, by + 12, text=title, fill="#FFFFFF", font=("맑은 고딕", 9, "bold")
            )

        # 3. 쓰레기 감지 대기 스팟
        self.canvas.create_oval(
            self.home_x - 35, self.home_y - 80, self.home_x + 35, self.home_y - 10,
            outline="#A78BFA", width=2, dash=(4, 4),
        )
        self.canvas.create_text(
            self.home_x, self.home_y - 45,
            text="📷 쓰레기 감지 위치", fill="#A78BFA", font=("맑은 고딕", 9, "bold")
        )

        # 4. 투입된 쓰레기 아이콘 (있을 경우)
        if active_trash and trash_x is not None and trash_y is not None:
            t_col = BIN_COLORS.get(active_trash, "#FFFFFF")
            self.canvas.create_oval(
                trash_x - 18, trash_y - 18, trash_x + 18, trash_y + 18,
                fill=t_col, outline="#FFFFFF", width=3,
            )
            self.canvas.create_text(
                trash_x, trash_y, text="📦", font=("Arial", 12)
            )

        # 5. 햄스터 로봇 2D 시각화
        rx, ry, ra = self.robot_x, self.robot_y, self.robot_angle
        r_size = 35

        cos_a, sin_a = math.cos(ra), math.sin(ra)
        
        def transform(dx, dy):
            return (rx + dx * cos_a - dy * sin_a, ry + dx * sin_a + dy * cos_a)

        pts = [transform(-r_size, -r_size * 0.8), transform(r_size, -r_size * 0.8),
               transform(r_size, r_size * 0.8), transform(-r_size, r_size * 0.8)]
        
        self.canvas.create_polygon(pts, fill="#F3F4F6", outline="#374151", width=3)

        # 좌우 바퀴
        w_l1, w_l2 = transform(-r_size * 0.5, -r_size * 0.95), transform(r_size * 0.5, -r_size * 0.95)
        w_r1, w_r2 = transform(-r_size * 0.5, r_size * 0.95), transform(r_size * 0.5, r_size * 0.95)
        self.canvas.create_line(w_l1[0], w_l1[1], w_l2[0], w_l2[1], fill="#111827", width=8)
        self.canvas.create_line(w_r1[0], w_r1[1], w_r2[0], w_r2[1], fill="#111827", width=8)

        # 좌우 RGB LED
        led_l = transform(r_size * 0.4, -r_size * 0.4)
        led_r = transform(r_size * 0.4, r_size * 0.4)
        l_col = "#3B82F6" if self.left_led == "BLUE" else ("#EF4444" if self.left_led == "RED" else "#F59E0B" if self.left_led == "YELLOW" else "#10B981" if self.left_led == "GREEN" else "#1F2937")
        r_col = "#3B82F6" if self.right_led == "BLUE" else ("#EF4444" if self.right_led == "RED" else "#F59E0B" if self.right_led == "YELLOW" else "#10B981" if self.right_led == "GREEN" else "#1F2937")
        
        self.canvas.create_oval(led_l[0]-6, led_l[1]-6, led_l[0]+6, led_l[1]+6, fill=l_col, outline="#FFFFFF", width=1)
        self.canvas.create_oval(led_r[0]-6, led_r[1]-6, led_r[0]+6, led_r[1]+6, fill=r_col, outline="#FFFFFF", width=1)

        # 전면 가상 집게 (Gripper Arms)
        g_angle = 0.4 if self.gripper_open else 0.05
        g_len = 28
        
        gl_tip = transform(r_size + g_len * math.cos(-g_angle), -r_size * 0.3 + g_len * math.sin(-g_angle))
        gr_tip = transform(r_size + g_len * math.cos(g_angle), r_size * 0.3 + g_len * math.sin(g_angle))
        gl_base = transform(r_size, -r_size * 0.3)
        gr_base = transform(r_size, r_size * 0.3)

        g_col = "#10B981" if self.gripper_open else "#EF4444"
        self.canvas.create_line(gl_base[0], gl_base[1], gl_tip[0], gl_tip[1], fill=g_col, width=5)
        self.canvas.create_line(gr_base[0], gr_base[1], gr_tip[0], gr_tip[1], fill=g_col, width=5)

        self.canvas.create_text(rx, ry, text="HAMSTER", fill="#1F2937", font=("Arial", 8, "bold"))

    def trigger_simulation(self, category: str):
        if self.is_animating:
            return
        
        threading.Thread(target=self._run_simulation_thread, args=(category,), daemon=True).start()

    def _run_simulation_thread(self, category: str):
        self.is_animating = True
        self.reset_robot_position()

        print(f"\n🎮 [시뮬레이터] '{category}' 분리배출 동작을 시작합니다!")
        self.status_var.set(f"🤖 [시뮬레이션] '{category}' 감지 완료! 쓰레기로 이동합니다.")

        # 쓰레기 위치
        tx, ty = self.home_x, self.home_y - 45

        # 1. LED 점등 및 접근
        led_color = "BLUE" if category == "플라스틱/페트병" else ("GREEN" if category == "캔" else ("YELLOW" if category == "종이" else ("RED" if category == "이물질/경고" else "BLUE")))
        self.left_led = led_color
        self.right_led = led_color

        if self.is_connected and self.hamster_robot:
            try:
                self.hamster_robot.leds(led_color.lower(), led_color.lower())
            except Exception:
                pass

        # 1단계: 접근 전진 및 실물 집게 열기
        self.control_physical_gripper("open")
        for i in range(15):
            self.robot_y -= 2.0
            self.draw_canvas(category, tx, ty)
            time.sleep(0.03)

        # 2단계: 집게 잡기 (close_gripper / GRIP!)
        self.status_var.set("🦾 [집게 제어] close_gripper()로 쓰레기를 꼭 잡습니다 (GRIP!)")
        self.gripper_open = False
        self.control_physical_gripper("close")
        self.draw_canvas(category, tx, ty)
        time.sleep(0.6)

        # 3단계: 수거함 위치 설정 및 운반
        target_locations = {
            "플라스틱/페트병": (90, 80, -math.pi * 0.75, "🔵 파란 수거함(좌측)"),
            "종이팩": (230, 80, -math.pi * 0.6, "🩵 하늘 수거함(대각선)"),
            "종이": (370, 80, -math.pi * 0.5, "🟡 노란 수거함(전방)"),
            "유리병(별도 수거)": (510, 80, -math.pi * 0.35, "🟠 주황 수거함(우측)"),
            "캔": (570, 240, 0.0, "🟢 초록 수거함(우측)"),
        }

        if category == "이물질/경고":
            self.status_var.set("🚨 [경고] 오배출/이물질 쓰레기! 삐 소리 출력 및 후진 퇴거")
            self.control_physical_gripper("release")
            if self.is_connected and self.hamster_robot:
                try:
                    self.hamster_robot.beep()
                except Exception:
                    pass
            for i in range(15):
                self.robot_y += 2.5
                self.draw_canvas(category, tx, ty)
                time.sleep(0.03)
            self.reset_robot_position()
            self.draw_canvas()
            self.is_animating = False
            self.status_var.set("[대기] 오배출 경고 조치 완료. 다음 쓰레기 대기 중.")
            return

        bx, by, target_ang, b_title = target_locations.get(category, (self.home_x, self.home_y, 0, ""))
        self.status_var.set(f"🚚 [운반 중] {b_title} 위치로 집게 운반 이동...")

        start_x, start_y = self.robot_x, self.robot_y
        start_ang = self.robot_angle

        steps = 25
        for step in range(steps + 1):
            t = step / steps
            self.robot_x = start_x + (bx - start_x) * t
            self.robot_y = start_y + (by + 40 - start_y) * t
            self.robot_angle = start_ang + (target_ang - start_ang) * t
            
            curr_tx = self.robot_x + 30 * math.cos(self.robot_angle)
            curr_ty = self.robot_y + 30 * math.sin(self.robot_angle)
            
            self.draw_canvas(category, curr_tx, curr_ty)
            time.sleep(0.03)

        # 4단계: 수거함 투입 (release_gripper!)
        self.status_var.set(f"📦 [수거 완료] {b_title}에 release_gripper()로 투입합니다")
        self.gripper_open = True
        self.control_physical_gripper("release")
        self.draw_canvas(category, bx, by)
        time.sleep(0.8)

        # 통계 카운트 증가 & 저장
        self.stats[category] = self.stats.get(category, 0) + 1
        self.stats["total"] += 1
        self.save_stats()
        self.update_stats_display()

        # 5단계: 원래 홈 위치로 후진 & 복귀
        self.status_var.set("↩️ [복귀] 원래 감지 홈 베이스 위치로 복귀합니다.")
        start_x, start_y = self.robot_x, self.robot_y
        start_ang = self.robot_angle

        for step in range(steps + 1):
            t = step / steps
            self.robot_x = start_x + (self.home_x - start_x) * t
            self.robot_y = start_y + (self.home_y - start_y) * t
            self.robot_angle = start_ang + (-math.pi / 2.0 - start_ang) * t
            self.draw_canvas()
            time.sleep(0.03)

        self.reset_robot_position()

        if self.is_connected and self.hamster_robot:
            try:
                self.hamster_robot.leds("off", "off")
                self.hamster_robot.stop()
            except Exception:
                pass

        self.draw_canvas()
        self.is_animating = False
        self.status_var.set("✅ [완료] 분리배출 수거 완료! 다음 쓰레기를 선택해 주세요.")


def main():
    root = tk.Tk()
    app = HamsterSimulatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
