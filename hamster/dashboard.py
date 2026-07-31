"""
Hamster Bot Telemetry Dashboard (Pygame GUI)
============================================
- Modern Dark-themed Telemetry & Control Dashboard
- Real-time 2D Robot Visualization
- Visual Sensor Gauges (Floor IR, Proximity IR)
- State Machine Status & Live System Event Logs
- Mode Switching (Autonomous <-> Manual Keyboard Control)
"""

import sys
import time
import math
import pygame
from typing import Optional

from hamster.autonomous_driver import AutonomousDriver, TelemetryData

# --- Theme Colors ---
COLOR_BG          = (15, 23, 42)
COLOR_CARD        = (30, 41, 59)
COLOR_CARD_BORDER = (51, 65, 85)
COLOR_TEXT        = (241, 245, 249)
COLOR_SUBTEXT     = (148, 163, 184)

COLOR_PRIMARY     = (59, 130, 246)
COLOR_SUCCESS     = (34, 197, 94)
COLOR_WARNING     = (234, 179, 8)
COLOR_DANGER      = (239, 68, 68)
COLOR_CYAN        = (6, 182, 212)
COLOR_PURPLE      = (168, 85, 247)

STATE_COLOR_MAP = {
    "CRUISING": COLOR_SUCCESS,
    "OBSTACLE_DETOUR": COLOR_WARNING,
    "STOP_LINE": COLOR_PRIMARY,
    "AUTO_PARKING": COLOR_PURPLE,
    "EMERGENCY_STOP": COLOR_DANGER,
    "MANUAL": COLOR_CYAN,
}


class DashboardApp:
    def __init__(self, driver: AutonomousDriver):
        self.driver = driver
        self.telemetry = driver.telemetry

        pygame.init()
        pygame.display.set_caption("Hamster Bot Autonomous Driving Dashboard")

        self.width = 900
        self.height = 580
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont("malgungothic", 20, bold=True)
        self.font_header = pygame.font.SysFont("malgungothic", 16, bold=True)
        self.font_body = pygame.font.SysFont("malgungothic", 13)
        self.font_mono = pygame.font.SysFont("consolas", 12)

        self.robot_angle = 0.0

    def draw_card(self, rect, title="", border_color=COLOR_CARD_BORDER):
        pygame.draw.rect(self.screen, COLOR_CARD, rect, border_radius=10)
        pygame.draw.rect(self.screen, border_color, rect, width=1, border_radius=10)
        if title:
            self.screen.blit(self.font_header.render(title, True, COLOR_TEXT), (rect.x + 15, rect.y + 12))

    def draw_gauge(self, x, y, w, h, value, max_val, label, val_text, color=COLOR_PRIMARY):
        self.screen.blit(self.font_body.render(label, True, COLOR_SUBTEXT), (x, y))
        vs = self.font_mono.render(val_text, True, COLOR_TEXT)
        self.screen.blit(vs, (x + w - vs.get_width(), y))
        bar_y = y + 20
        pygame.draw.rect(self.screen, (15, 23, 42), (x, bar_y, w, h), border_radius=4)
        fill = int(w * max(0.0, min(1.0, abs(value) / max_val)))
        if fill > 0:
            pygame.draw.rect(self.screen, color, (x, bar_y, fill, h), border_radius=4)

    def draw_left_panel(self, snap):
        # Header
        r = pygame.Rect(20, 15, 420, 65)
        self.draw_card(r)
        self.screen.blit(self.font_title.render("햄스터 AI 자율주행", True, COLOR_TEXT), (35, 25))

        mode = snap["mode"]
        mc = COLOR_SUCCESS if mode == "AUTONOMOUS" else COLOR_CYAN
        pygame.draw.rect(self.screen, mc, (290, 28, 130, 24), border_radius=12)
        self.screen.blit(self.font_header.render(f"모드: {mode}", True, (255, 255, 255)), (300, 30))

        hw = "HW 연결됨" if snap["hardware_connected"] else "시뮬레이션"
        hc = COLOR_SUCCESS if snap["hardware_connected"] else COLOR_WARNING
        self.screen.blit(self.font_body.render(hw, True, hc), (35, 55))

        # State
        r = pygame.Rect(20, 90, 420, 80)
        state = snap["state"]
        sc = STATE_COLOR_MAP.get(state, COLOR_PRIMARY)
        self.draw_card(r, "주행 상태 (FSM)", border_color=sc)
        pygame.draw.rect(self.screen, sc, (35, 120, 150, 26), border_radius=6)
        self.screen.blit(self.font_header.render(state, True, (255, 255, 255)), (42, 122))
        self.screen.blit(self.font_body.render(snap["state_desc"], True, COLOR_TEXT), (195, 124))

        # Floor Sensors
        r = pygame.Rect(20, 180, 420, 110)
        self.draw_card(r, "바닥 센서 (Floor IR)")
        self.draw_gauge(35, 212, 180, 12, snap["left_floor"], 100, "왼쪽", f"{snap['left_floor']}", COLOR_PRIMARY)
        self.draw_gauge(240, 212, 180, 12, snap["right_floor"], 100, "오른쪽", f"{snap['right_floor']}", COLOR_PRIMARY)
        note = "정지선 감지" if snap["left_floor"] < 25 and snap["right_floor"] < 25 else "주행 중"
        self.screen.blit(self.font_body.render(f"상태: {note}", True, COLOR_SUBTEXT), (35, 255))

        # Proximity Sensors
        r = pygame.Rect(20, 300, 420, 110)
        self.draw_card(r)
        self.screen.blit(self.font_header.render("전방 근접 센서 (Proximity IR)", True, COLOR_TEXT), (35, 312))
        plc = COLOR_DANGER if snap["left_prox"] > 30 else COLOR_SUCCESS
        prc = COLOR_DANGER if snap["right_prox"] > 30 else COLOR_SUCCESS
        self.draw_gauge(35, 335, 180, 12, snap["left_prox"], 100, "왼쪽", f"{snap['left_prox']}", plc)
        self.draw_gauge(240, 335, 180, 12, snap["right_prox"], 100, "오른쪽", f"{snap['right_prox']}", prc)
        on = "장애물 감지!" if snap["left_prox"] > 30 or snap["right_prox"] > 30 else "경로 확보"
        self.screen.blit(self.font_body.render(f"상태: {on}", True, COLOR_SUBTEXT), (35, 378))

    def draw_robot(self, snap):
        r = pygame.Rect(460, 15, 420, 290)
        self.draw_card(r, "2D 로봇 시각화")

        lw = snap["left_wheel"]
        rw = snap["right_wheel"]
        self.robot_angle += (rw - lw) * 0.05

        cx, cy = 670, 160
        w, h = 90, 120

        surf = pygame.Surface((w + 50, h + 50), pygame.SRCALPHA)
        rcx, rcy = (w + 50) // 2, (h + 50) // 2

        # Wheels
        lwc = COLOR_PRIMARY if lw != 0 else COLOR_CARD_BORDER
        rwc = COLOR_PRIMARY if rw != 0 else COLOR_CARD_BORDER
        pygame.draw.rect(surf, lwc, (rcx - w//2 - 10, rcy - h//3, 10, 45), border_radius=3)
        pygame.draw.rect(surf, rwc, (rcx + w//2, rcy - h//3, 10, 45), border_radius=3)

        # Body
        bc = (71, 85, 105) if snap["state"] != "EMERGENCY_STOP" else COLOR_DANGER
        pygame.draw.rect(surf, bc, (rcx - w//2, rcy - h//2, w, h), border_radius=18)
        pygame.draw.rect(surf, COLOR_CARD_BORDER, (rcx - w//2, rcy - h//2, w, h), width=2, border_radius=18)

        # LEDs
        lc = STATE_COLOR_MAP.get(snap["state"], COLOR_SUCCESS)
        pygame.draw.circle(surf, lc, (rcx - 22, rcy - h//2 + 18), 7)
        pygame.draw.circle(surf, lc, (rcx + 22, rcy - h//2 + 18), 7)

        # Proximity beams
        if snap["left_prox"] > 5:
            bh = int(snap["left_prox"] * 0.5)
            pygame.draw.line(surf, COLOR_WARNING, (rcx - 22, rcy - h//2), (rcx - 30, rcy - h//2 - bh), 2)
        if snap["right_prox"] > 5:
            bh = int(snap["right_prox"] * 0.5)
            pygame.draw.line(surf, COLOR_WARNING, (rcx + 22, rcy - h//2), (rcx + 30, rcy - h//2 - bh), 2)

        # Floor dots
        lfc = COLOR_SUCCESS if snap["left_floor"] > 50 else COLOR_DANGER
        rfc = COLOR_SUCCESS if snap["right_floor"] > 50 else COLOR_DANGER
        pygame.draw.circle(surf, lfc, (rcx - 18, rcy + h//2 - 22), 5)
        pygame.draw.circle(surf, rfc, (rcx + 18, rcy + h//2 - 22), 5)

        rotated = pygame.transform.rotate(surf, math.degrees(self.robot_angle))
        self.screen.blit(rotated, rotated.get_rect(center=(cx, cy)).topleft)

        wt = self.font_mono.render(f"바퀴 - L: {lw}  R: {rw}", True, COLOR_TEXT)
        self.screen.blit(wt, (cx - wt.get_width()//2, 275))

    def draw_log(self, snap):
        r = pygame.Rect(460, 315, 420, 245)
        self.draw_card(r, "시스템 이벤트 로그")

        y = 350
        for line in snap["log_messages"][-8:]:
            lc = COLOR_TEXT
            if "ALERT" in line or "Emergency" in line:
                lc = COLOR_DANGER
            elif "Obstacle" in line:
                lc = COLOR_WARNING
            elif "Switched" in line:
                lc = COLOR_CYAN
            self.screen.blit(self.font_mono.render(line, True, lc), (475, y))
            y += 21

        guide = "[TAB] 모드전환  [SPACE] 비상정지  [R] 리셋  [WASD] 수동  [ESC] 종료"
        self.screen.blit(self.font_body.render(guide, True, COLOR_SUBTEXT), (475, 540))

    def handle_input(self):
        keys = pygame.key.get_pressed()
        lw, rw = 0, 0
        speed = 50

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            lw += speed; rw += speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            lw -= speed; rw -= speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            lw -= speed // 2; rw += speed // 2
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            lw += speed // 2; rw -= speed // 2

        self.driver.set_manual_wheels(lw, rw)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_TAB:
                    self.driver.toggle_mode()
                elif event.key == pygame.K_SPACE:
                    self.driver.emergency_stop()
                elif event.key == pygame.K_r:
                    self.driver.reset_emergency()
        return True

    def run_loop(self):
        self.driver.start()
        running = True
        last = time.time()

        try:
            while running:
                now = time.time()
                dt = now - last
                last = now

                self.driver.update_cycle(dt)
                running = self.handle_input()

                snap = self.telemetry.get_snapshot()
                self.screen.fill(COLOR_BG)
                self.draw_left_panel(snap)
                self.draw_robot(snap)
                self.draw_log(snap)
                pygame.display.flip()
                self.clock.tick(30)
        finally:
            self.driver.stop()
            pygame.quit()


def launch_dashboard(hamster=None):
    driver = AutonomousDriver(hamster=hamster)
    app = DashboardApp(driver)
    app.run_loop()


if __name__ == "__main__":
    launch_dashboard()
