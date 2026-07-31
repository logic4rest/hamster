"""
Hamster Bot Smart Autonomous Driving Core Engine
================================================
- Proportional-Integral-Derivative (PID) Line Tracer
- Multi-Sensor Fusion State Machine (FSM)
- Obstacle Avoidance & Detour Routing
- Stop Line / Intersection Detection & Auto-Parking
- Thread-safe Telemetry Data Interface
"""

import time
import math
import threading
from typing import Dict, Any, Optional


class MockHamster:
    """Mock class for simulation when hardware is not connected"""
    def __init__(self):
        self._l_floor = 75
        self._r_floor = 75
        self._l_prox = 10
        self._r_prox = 10
        self._l_wheel = 0
        self._r_wheel = 0

    def left_floor(self): return int(self._l_floor)
    def right_floor(self): return int(self._r_floor)
    def left_proximity(self): return int(self._l_prox)
    def right_proximity(self): return int(self._r_prox)
    def wheels(self, l, r):
        self._l_wheel = l
        self._r_wheel = r
    def leds(self, l, r): pass
    def beep(self): pass
    def stop(self):
        self._l_wheel = 0
        self._r_wheel = 0


class PIDController:
    """PID Controller for smooth line tracing"""
    def __init__(self, kp: float = 0.75, ki: float = 0.01, kd: float = 0.25):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0.0
        self.integral = 0.0

    def reset(self):
        self.prev_error = 0.0
        self.integral = 0.0

    def compute(self, error: float, dt: float = 0.03) -> float:
        self.integral += error * dt
        self.integral = max(-50.0, min(50.0, self.integral))
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error
        return (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)


class TelemetryData:
    """Thread-safe state and sensor data container for real-time UI telemetry"""
    def __init__(self):
        self.lock = threading.Lock()
        self.mode = "AUTONOMOUS"
        self.state = "CRUISING"
        self.state_desc = "Line Tracing Active"
        self.left_floor = 80
        self.right_floor = 80
        self.left_prox = 0
        self.right_prox = 0
        self.left_wheel = 0
        self.right_wheel = 0
        self.target_speed = 45
        self.log_messages = []
        self.hardware_connected = False

    def update_sensors(self, lf, rf, lp, rp, lw, rw):
        with self.lock:
            self.left_floor = lf
            self.right_floor = rf
            self.left_prox = lp
            self.right_prox = rp
            self.left_wheel = lw
            self.right_wheel = rw

    def add_log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        with self.lock:
            self.log_messages.append(f"[{timestamp}] {msg}")
            if len(self.log_messages) > 15:
                self.log_messages.pop(0)

    def get_snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "mode": self.mode,
                "state": self.state,
                "state_desc": self.state_desc,
                "left_floor": self.left_floor,
                "right_floor": self.right_floor,
                "left_prox": self.left_prox,
                "right_prox": self.right_prox,
                "left_wheel": self.left_wheel,
                "right_wheel": self.right_wheel,
                "target_speed": self.target_speed,
                "log_messages": list(self.log_messages),
                "hardware_connected": self.hardware_connected,
            }


class AutonomousDriver:
    """Main state machine and driver controller for Hamster S"""
    def __init__(self, hamster=None, telemetry: Optional[TelemetryData] = None):
        self.current_lw = 0
        self.current_rw = 0

        if hamster is None:
            try:
                from roboid import Hamster
                self.hamster = Hamster()
                time.sleep(1.0)
                self.hardware_connected = True
            except Exception as e:
                print(f"[WARN] Hamster hardware not found: {e}. Simulation Mode.")
                self.hamster = MockHamster()
                self.hardware_connected = False
        else:
            self.hamster = hamster
            self.hardware_connected = not isinstance(hamster, MockHamster)

        self.telemetry = telemetry or TelemetryData()
        self.telemetry.hardware_connected = self.hardware_connected

        self.pid = PIDController(kp=0.75, ki=0.01, kd=0.25)

        self.running = False
        self.base_speed = 45
        self.obstacle_threshold = 30
        self.stop_line_threshold = 25

        # Detour Sub-State
        self.detour_step = 0
        self.detour_timer = 0.0

        # Parking Sub-State
        self.parking_step = 0
        self.parking_timer = 0.0

        # Manual Override
        self.manual_lw = 0
        self.manual_rw = 0

    def start(self):
        self.running = True
        self.telemetry.add_log("Autonomous Driver Started")

    def stop(self):
        self.running = False
        try:
            self.hamster.wheels(0, 0)
            self.current_lw = 0
            self.current_rw = 0
            self.hamster.leds("off", "off")
        except Exception:
            pass
        self.telemetry.add_log("Autonomous Driver Stopped")

    def set_manual_wheels(self, lw: int, rw: int):
        self.manual_lw = lw
        self.manual_rw = rw

    def emergency_stop(self):
        """Manual emergency stop triggered by user (Space key)"""
        self._set_wheels(0, 0)
        self.hamster.leds("red", "red")
        with self.telemetry.lock:
            self.telemetry.state = "EMERGENCY_STOP"
            self.telemetry.state_desc = "Manual Emergency Brake"
        self.telemetry.add_log("Manual Emergency Brake Activated")

    def reset_emergency(self):
        with self.telemetry.lock:
            if self.telemetry.state == "EMERGENCY_STOP":
                self.telemetry.state = "CRUISING" if self.telemetry.mode == "AUTONOMOUS" else "MANUAL"
                self.telemetry.state_desc = "Emergency Reset"
                self.telemetry.add_log("Emergency State Reset")
                self.pid.reset()
                if not self.running:
                    self.running = True

    def toggle_mode(self):
        with self.telemetry.lock:
            if self.telemetry.mode == "AUTONOMOUS":
                self.telemetry.mode = "MANUAL"
                self.telemetry.state = "MANUAL"
                self.telemetry.state_desc = "Manual Keyboard Control"
                self.telemetry.add_log("Switched to MANUAL Mode")
            else:
                self.telemetry.mode = "AUTONOMOUS"
                self.telemetry.state = "CRUISING"
                self.telemetry.state_desc = "Autonomous Line Tracing"
                self.telemetry.add_log("Switched to AUTONOMOUS Mode")
                self.pid.reset()

    def _set_wheels(self, lw: int, rw: int):
        self.current_lw = lw
        self.current_rw = rw
        try:
            self.hamster.wheels(lw, rw)
        except Exception:
            pass

    def update_cycle(self, dt: float = 0.03):
        if not self.running:
            return

        # 1. Read Sensors
        try:
            lf = self.hamster.left_floor()
            rf = self.hamster.right_floor()
            lp = self.hamster.left_proximity()
            rp = self.hamster.right_proximity()
        except Exception as e:
            self.telemetry.add_log(f"Sensor read error: {e}")
            return

        self.telemetry.update_sensors(lf, rf, lp, rp, self.current_lw, self.current_rw)

        # 2. Emergency Stop stays locked until reset
        if self.telemetry.state == "EMERGENCY_STOP":
            self._set_wheels(0, 0)
            self.hamster.leds("red", "red")
            return

        # 3. Manual Mode
        if self.telemetry.mode == "MANUAL":
            self._set_wheels(self.manual_lw, self.manual_rw)
            if self.manual_lw != 0 or self.manual_rw != 0:
                self.hamster.leds("cyan", "cyan")
            else:
                self.hamster.leds("off", "off")
            return

        # 4. Autonomous FSM
        current_state = self.telemetry.state

        # --- Trigger: Obstacle ---
        if current_state == "CRUISING" and (lp > self.obstacle_threshold or rp > self.obstacle_threshold):
            self.telemetry.state = "OBSTACLE_DETOUR"
            self.detour_step = 0
            self.detour_timer = time.time()
            self.telemetry.state_desc = "Obstacle Detected! Detour"
            self.telemetry.add_log(f"Obstacle! (L:{lp}, R:{rp}) -> Detour")
            self.hamster.leds("yellow", "yellow")
            try:
                self.hamster.beep()
            except Exception:
                pass

        # --- Trigger: Stop Line ---
        elif current_state == "CRUISING" and (lf < self.stop_line_threshold and rf < self.stop_line_threshold):
            self.telemetry.state = "STOP_LINE"
            self.parking_timer = time.time()
            self.telemetry.state_desc = "Stop Line Detected"
            self.telemetry.add_log("Stop Line Detected!")
            self._set_wheels(0, 0)
            self.hamster.leds("blue", "blue")

        # --- CRUISING ---
        if self.telemetry.state == "CRUISING":
            self.hamster.leds("green", "green")

            if lf < 50 or rf < 50:
                error = rf - lf
                steering = self.pid.compute(error, dt)
                left_out = max(-100, min(100, int(self.base_speed - steering)))
                right_out = max(-100, min(100, int(self.base_speed + steering)))
            else:
                left_out = self.base_speed
                right_out = self.base_speed

            self._set_wheels(left_out, right_out)

        # --- OBSTACLE_DETOUR ---
        elif self.telemetry.state == "OBSTACLE_DETOUR":
            elapsed = time.time() - self.detour_timer
            if self.detour_step == 0:
                self.hamster.leds("yellow", "off")
                self._set_wheels(50, -30)
                if elapsed > 0.6:
                    self.detour_step = 1
                    self.detour_timer = time.time()
            elif self.detour_step == 1:
                self.hamster.leds("yellow", "yellow")
                self._set_wheels(45, 45)
                if elapsed > 1.0:
                    self.detour_step = 2
                    self.detour_timer = time.time()
            elif self.detour_step == 2:
                self.hamster.leds("off", "yellow")
                self._set_wheels(-30, 50)
                if elapsed > 0.7 or (lf < 50 or rf < 50):
                    self.detour_step = 3
                    self.detour_timer = time.time()
            elif self.detour_step == 3:
                if lf < 60 or rf < 60 or elapsed > 0.5:
                    self.telemetry.state = "CRUISING"
                    self.telemetry.state_desc = "Resumed Line Tracing"
                    self.telemetry.add_log("Detour complete -> Resumed")
                    self.pid.reset()

        # --- STOP_LINE ---
        elif self.telemetry.state == "STOP_LINE":
            elapsed = time.time() - self.parking_timer
            if elapsed < 1.5:
                self._set_wheels(0, 0)
                self.hamster.leds("blue", "blue")
            else:
                self.telemetry.state = "AUTO_PARKING"
                self.parking_step = 0
                self.parking_timer = time.time()
                self.telemetry.state_desc = "Auto-Parking"
                self.telemetry.add_log("Starting Auto-Parking")

        # --- AUTO_PARKING ---
        elif self.telemetry.state == "AUTO_PARKING":
            elapsed = time.time() - self.parking_timer
            if self.parking_step == 0:
                self.hamster.leds("magenta", "magenta")
                self._set_wheels(-35, -35)
                if elapsed > 1.2:
                    self.parking_step = 1
                    self.parking_timer = time.time()
            elif self.parking_step == 1:
                self._set_wheels(0, 0)
                self.hamster.leds("green", "green")
                try:
                    self.hamster.beep()
                except Exception:
                    pass
                if elapsed > 1.0:
                    self.telemetry.state = "CRUISING"
                    self.telemetry.state_desc = "Parking Done. Resuming"
                    self.telemetry.add_log("Parking complete -> Resuming")
                    self.pid.reset()
