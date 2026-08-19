"""
Logitech C922 Pro 웹캠 실시간 스냅샷 캡처 도구
====================================================================================================
- C922 Pro 웹캠 영상 프레임을 캡처하여 captures/c922_snapshot.jpg 파일로 저장
- Antigravity AI 에이전트가 view_file 도구를 통해 웹캠 화면을 직접 볼 수 있도록 지원
"""

import sys
import time
from pathlib import Path
import cv2

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).parent.parent
CAPTURES_DIR = PROJECT_ROOT / "captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

SNAPSHOT_PATH = CAPTURES_DIR / "c922_snapshot.jpg"


def capture_snapshot():
    print("[INFO] Logitech C922 Pro 웹캠 연결 중...")
    cap = None
    for idx in [0, 1, 2, 3]:
        temp_cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if temp_cap.isOpened():
            ret, frame = temp_cap.read()
            if ret and frame is not None:
                print(f"[INFO] C922 웹캠 연결 성공! (인덱스: {idx})")
                cap = temp_cap
                break
        temp_cap.release()

    if cap is None:
        print("[ERROR] C922 웹캠을 찾을 수 없습니다.")
        return None

    # 카메라 화질 안정화 대기 (10프레임 무시)
    for _ in range(10):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if ret and frame is not None:
        frame = cv2.flip(frame, 1)  # 좌우 반전
        cv2.imwrite(str(SNAPSHOT_PATH), frame)
        print(f"[OK] C922 스냅샷 캡처 완료! 경로: {SNAPSHOT_PATH.resolve()}")
        return SNAPSHOT_PATH
    else:
        print("[ERROR] 이미지를 캡처하지 못했습니다.")
        return None


if __name__ == "__main__":
    capture_snapshot()
