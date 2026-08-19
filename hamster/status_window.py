"""
햄스터 로봇 실시간 상태 모니터링 미니 HUD 창 (v4.4)
====================================================================================================
- 햄스터 로봇의 연결 상태, 전방 적외선 센서값, 집게 상태, LED 색상, 주행 모션 상태를
  작은 플로팅 창(Always on Top)으로 실시간 렌더링
"""

import math
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk

# 윈도우 콘솔 UTF-8 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class HamsterStatusHUD:
    """햄스터 로봇 실시간 상태 전용 미니 플로팅 창 클래스"""

    def __init__(self):
        self.root = None
        self.thread = None
        self.running = False

        # 실시간 모니터링 상태 데이터
        self.state_data = {
            "connection": "🟢 연결됨 (BLE)",
            "motion": "대기 중 (Standby)",
            "category": "없음",
            "gripper": "열림 (OPEN)",
            "left_prox": 0,
            "right_prox": 0,
            "led": "OFF",
            "battery": "정상",
        }

        self._start_window_thread()

    def _start_window_thread(self):
        """Tkinter 미니 창을 백그라운드 스레드에서 안전하게 실행"""
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()

    def _run_gui(self):
        self.root = tk.Tk()
        self.root.title("🐹 햄스터 로봇 실시간 상태창")
        self.root.geometry("360x270+50+50")
        self.root.configure(bg="#1E1E2E")
        self.root.resizable(False, False)

        # 항상 맨 위에 표시 (Always on Top)
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        # 1. 헤더 프레임
        header = tk.Frame(self.root, bg="#2B2B3D", height=40)
        header.pack(fill=tk.X)

        self.lbl_title = tk.Label(
            header,
            text="🐹 햄스터 봇 실시간 대시보드",
            font=("맑은 고딕", 12, "bold"),
            bg="#2B2B3D",
            fg="#F8F8F2",
        )
        self.lbl_title.pack(side=tk.LEFT, padx=12, pady=8)

        self.lbl_conn = tk.Label(
            header,
            text="🟢 연결됨",
            font=("맑은 고딕", 10, "bold"),
            bg="#2B2B3D",
            fg="#50FA7B",
        )
        self.lbl_conn.pack(side=tk.RIGHT, padx=12)

        # 2. 메인 컨텐츠 그리드
        body = tk.Frame(self.root, bg="#1E1E2E", padx=15, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        # (1) 동작 상태
        tk.Label(body, text="🚚 현재 모션:", font=("맑은 고딕", 10, "bold"), bg="#1E1E2E", fg="#89DDFF").grid(row=0, column=0, sticky="w", pady=3)
        self.lbl_motion = tk.Label(body, text="대기 중", font=("맑은 고딕", 10), bg="#1E1E2E", fg="#F8F8F2")
        self.lbl_motion.grid(row=0, column=1, sticky="w", padx=10)

        # (2) 감지된 쓰레기
        tk.Label(body, text="🏷️ 감지 쓰레기:", font=("맑은 고딕", 10, "bold"), bg="#1E1E2E", fg="#FF79C6").grid(row=1, column=0, sticky="w", pady=3)
        self.lbl_category = tk.Label(body, text="없음", font=("맑은 고딕", 10, "bold"), bg="#1E1E2E", fg="#BD93F9")
        self.lbl_category.grid(row=1, column=1, sticky="w", padx=10)

        # (3) 집게 상태
        tk.Label(body, text="🦾 집게 (Gripper):", font=("맑은 고딕", 10, "bold"), bg="#1E1E2E", fg="#F1FA8C").grid(row=2, column=0, sticky="w", pady=3)
        self.lbl_gripper = tk.Label(body, text="열림 (OPEN)", font=("맑은 고딕", 10, "bold"), bg="#1E1E2E", fg="#50FA7B")
        self.lbl_gripper.grid(row=2, column=1, sticky="w", padx=10)

        # (4) LED 상태
        tk.Label(body, text="💡 LED 표시:", font=("맑은 고딕", 10, "bold"), bg="#1E1E2E", fg="#BD93F9").grid(row=3, column=0, sticky="w", pady=3)
        self.lbl_led = tk.Label(body, text="OFF ⚪", font=("맑은 고딕", 10), bg="#1E1E2E", fg="#F8F8F2")
        self.lbl_led.grid(row=3, column=1, sticky="w", padx=10)

        # (5) 전방 근접 센서 바 (Left / Right Proximity)
        tk.Label(body, text="📡 전방 적외선 센서:", font=("맑은 고딕", 10, "bold"), bg="#1E1E2E", fg="#FFB86C").grid(row=4, column=0, sticky="w", pady=6)
        
        prox_frame = tk.Frame(body, bg="#1E1E2E")
        prox_frame.grid(row=4, column=1, sticky="w", padx=10)

        self.lbl_prox_val = tk.Label(prox_frame, text="좌: 0 | 우: 0", font=("맑은 고딕", 9), bg="#1E1E2E", fg="#F8F8F2")
        self.lbl_prox_val.pack(anchor="w")

        # Proximity Progress Bar Indicators
        self.pbar_left = ttk.Progressbar(prox_frame, orient="horizontal", length=80, mode="determinate")
        self.pbar_left.pack(side=tk.LEFT, padx=(0, 5))
        self.pbar_right = ttk.Progressbar(prox_frame, orient="horizontal", length=80, mode="determinate")
        self.pbar_right.pack(side=tk.LEFT)

        # 3. 하단 안내
        footer = tk.Label(
            self.root,
            text="💡 실시간 햄스터 하드웨어 상태 동기화 중",
            font=("맑은 고딕", 8),
            bg="#2B2B3D",
            fg="#6272A4",
            pady=4,
        )
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        self.running = True
        self._periodic_update()
        self.root.mainloop()

    def _periodic_update(self):
        """Tkinter 메인 스레드 UI 동기화 매크로 루프"""
        if not self.running or self.root is None:
            return

        try:
            self.lbl_motion.config(text=self.state_data["motion"])
            self.lbl_category.config(text=self.state_data["category"])
            self.lbl_gripper.config(text=self.state_data["gripper"])

            # LED 색상별 글자 및 이모지
            led_val = self.state_data["led"]
            if led_val == "blue":
                self.lbl_led.config(text="파란색 🔵", fg="#89DDFF")
            elif led_val == "cyan":
                self.lbl_led.config(text="하늘색 🩵", fg="#80FFFF")
            elif led_val == "yellow":
                self.lbl_led.config(text="노란색 🟡", fg="#F1FA8C")
            elif led_val == "green":
                self.lbl_led.config(text="초록색 🟢", fg="#50FA7B")
            elif led_val == "red":
                self.lbl_led.config(text="빨간색 🔴", fg="#FF5555")
            else:
                self.lbl_led.config(text="OFF ⚪", fg="#F8F8F2")

            # 센서값 동기화
            lp = self.state_data["left_prox"]
            rp = self.state_data["right_prox"]
            self.lbl_prox_val.config(text=f"좌: {lp} | 우: {rp}")
            self.pbar_left["value"] = min(100, lp)
            self.pbar_right["value"] = min(100, rp)

        except Exception:
            pass

        if self.root:
            self.root.after(100, self._periodic_update)

    def update_status(
        self,
        motion: str = None,
        category: str = None,
        gripper: str = None,
        left_prox: int = None,
        right_prox: int = None,
        led: str = None,
    ):
        """상태 업데이트 메서드"""
        if motion is not None:
            self.state_data["motion"] = motion
        if category is not None:
            self.state_data["category"] = category
        if gripper is not None:
            self.state_data["gripper"] = gripper
        if left_prox is not None:
            self.state_data["left_prox"] = left_prox
        if right_prox is not None:
            self.state_data["right_prox"] = right_prox
        if led is not None:
            self.state_data["led"] = led


# 글로벌 인스턴스
status_hud = HamsterStatusHUD()
