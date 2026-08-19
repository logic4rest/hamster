"""
햄스터 로봇 4종 위치 북마크(Waypoint) & 번호 매핑 저장 관리자 (v4.2)
====================================================================================================
사용자 지정 4종 지정 슬롯:
  [1] 종이
  [2] 종이팩
  [3] 패트병(플라스틱) / 플라스틱/페트병
  [4] 캔
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).parent.parent
ROUTES_DIR   = PROJECT_ROOT / "routes"
LOGS_DIR     = PROJECT_ROOT / "logs"
CAPTURES_DIR = PROJECT_ROOT / "captures"

ROUTES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

WAYPOINTS_MASTER_PATH = ROUTES_DIR / "waypoints.json"
HISTORY_LOG_PATH       = LOGS_DIR / "history.log"
PROMPTS_LOG_PATH       = LOGS_DIR / "prompts.json"

NUMBERED_SLOTS = {
    "1": "종이",
    "2": "종이팩",
    "3": "플라스틱/페트병",
    "4": "캔",
}


class WaypointManager:
    """4종 번호 매핑 북마크 (1:종이, 2:종이팩, 3:패트병, 4:캔) 및 오차 보정 관리자"""

    def __init__(self):
        self.waypoints: Dict[str, Dict[str, Any]] = self._load_master_waypoints()
        self.prompts_history: List[Dict[str, Any]] = self._load_prompts_history()

    def _load_master_waypoints(self) -> Dict[str, Dict[str, Any]]:
        """마스터 북마크 파일 로드"""
        if WAYPOINTS_MASTER_PATH.exists():
            try:
                with open(WAYPOINTS_MASTER_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                self.log_event("ERROR", f"마스터 북마크 로드 실패: {e}")

        # 4종 지정 슬롯 기본 템플릿
        return {
            "1_종이": {
                "slot": "1",
                "name": "종이",
                "date": time.strftime("%Y-%m-%d"),
                "trajectory": [{"left": 35, "right": 35, "duration": 1.0}]
            },
            "2_종이팩": {
                "slot": "2",
                "name": "종이팩",
                "date": time.strftime("%Y-%m-%d"),
                "trajectory": [{"left": -20, "right": 35, "duration": 0.9}]
            },
            "3_플라스틱/페트병": {
                "slot": "3",
                "name": "플라스틱/페트병",
                "date": time.strftime("%Y-%m-%d"),
                "trajectory": [{"left": -35, "right": 35, "duration": 0.6}, {"left": 35, "right": 35, "duration": 0.7}]
            },
            "4_캔": {
                "slot": "4",
                "name": "캔",
                "date": time.strftime("%Y-%m-%d"),
                "trajectory": [{"left": 35, "right": -35, "duration": 0.6}, {"left": 35, "right": 35, "duration": 0.7}]
            }
        }

    def _load_prompts_history(self) -> List[Dict[str, Any]]:
        if PROMPTS_LOG_PATH.exists():
            try:
                with open(PROMPTS_LOG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []

    def log_event(self, event_type: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """히스토리 로그 기록"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{event_type}] {message}"
        if extra:
            log_line += f" | {json.dumps(extra, ensure_ascii=False)}"

        print(f"  📝 {log_line}")

        try:
            with open(HISTORY_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception:
            pass

        prompt_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": message,
            "extra": extra or {}
        }
        self.prompts_history.append(prompt_entry)
        try:
            with open(PROMPTS_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.prompts_history[-100:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def filter_trajectory_error(self, raw_trajectory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """주행 오차 최소화 노이즈 필터링"""
        filtered = []
        for step in raw_trajectory:
            left = step.get("left", 0)
            right = step.get("right", 0)
            dur = round(step.get("duration", 0), 2)

            if left == 0 and right == 0:
                continue
            if dur < 0.05:
                continue

            if filtered and filtered[-1]["left"] == left and filtered[-1]["right"] == right:
                filtered[-1]["duration"] = round(filtered[-1]["duration"] + dur, 2)
            else:
                filtered.append({
                    "left": left,
                    "right": right,
                    "duration": dur
                })

        return filtered if filtered else [{"left": 35, "right": 35, "duration": 1.0}]

    def save_slot(self, slot_num: str, trajectory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        4종 지정 번호 슬롯 저장:
          1 -> 종이
          2 -> 종이팩
          3 -> 패트병(플라스틱)
          4 -> 캔
        """
        slot_key = str(slot_num).strip()
        clean_name = NUMBERED_SLOTS.get(slot_key, "종이")
        clean_trajectory = self.filter_trajectory_error(trajectory)

        master_key = f"{slot_key}_{clean_name}"

        today_str = time.strftime("%Y%m%d")
        date_folder = ROUTES_DIR / today_str
        date_folder.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{slot_key}_{clean_name.replace('/', '_')}"
        partition_path = date_folder / f"{safe_filename}.json"

        waypoint_data = {
            "slot": slot_key,
            "name": clean_name,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "trajectory_steps": len(clean_trajectory),
            "trajectory": clean_trajectory
        }

        # 1. 마스터 저장
        self.waypoints[master_key] = waypoint_data
        self.waypoints[clean_name] = waypoint_data  # 이름 검색용 호환

        try:
            with open(WAYPOINTS_MASTER_PATH, "w", encoding="utf-8") as f:
                json.dump(self.waypoints, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_event("ERROR", f"마스터 저장 실패: {e}")

        # 2. 날짜별/슬롯별 파티셔닝 저장
        try:
            with open(partition_path, "w", encoding="utf-8") as f:
                json.dump(waypoint_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_event("ERROR", f"파티셔닝 저장 실패: {e}")

        # 종이 호환 파일 저장
        if slot_key == "1" or clean_name == "종이":
            paper_path = ROUTES_DIR / "paper_route.json"
            try:
                with open(paper_path, "w", encoding="utf-8") as f:
                    json.dump(clean_trajectory, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        self.log_event("WAYPOINT_SAVED", f"슬롯 [{slot_key}] '{clean_name}' 위치 저장 완료 ({len(clean_trajectory)}단계)", {
            "partition": str(partition_path)
        })

        return waypoint_data

    def get_waypoint(self, name_or_slot: str) -> Optional[List[Dict[str, Any]]]:
        """슬롯 번호 또는 이름 기반 위치 검색/호출"""
        query = str(name_or_slot).strip()

        # 슬롯 번호로 검색 (1, 2, 3, 4)
        if query in NUMBERED_SLOTS:
            slot_name = NUMBERED_SLOTS[query]
            master_key = f"{query}_{slot_name}"
            if master_key in self.waypoints:
                return self.waypoints[master_key].get("trajectory", [])
            if slot_name in self.waypoints:
                return self.waypoints[slot_name].get("trajectory", [])

        # 이름으로 검색 (종이, 종이팩, 플라스틱/페트병, 캔)
        if query in self.waypoints:
            return self.waypoints[query].get("trajectory", [])

        for wp_key, wp_data in self.waypoints.items():
            if query in wp_key or wp_key in query:
                return wp_data.get("trajectory", [])

        return None


waypoint_manager = WaypointManager()
