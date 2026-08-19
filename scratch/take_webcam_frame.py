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

out_dir = Path(r"C:\Users\User\.gemini\antigravity\brain\11ff0cde-0f06-4ef3-876e-c9ee53f4423f")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "webcam_live.jpg"

print("[INFO] 웹캠 스냅샷 촬영 시작...")

cap = None
for idx in [0, 1, 2]:
    for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
        try:
            c = cv2.VideoCapture(idx, backend)
            if c.isOpened():
                # 20프레임 오토 익스포저 웜업
                valid_frame = None
                for _ in range(25):
                    ret, frame = c.read()
                    if ret and frame is not None and frame.mean() > 10:
                        valid_frame = frame
                    time.sleep(0.02)
                c.release()

                if valid_frame is not None:
                    print(f"[OK] 카메라 인덱스 {idx} 캡처 성공! (평균 밝기: {valid_frame.mean():.1f})")
                    cap_frame = cv2.flip(valid_frame, 1)
                    cv2.imwrite(str(out_path), cap_frame)
                    sys.exit(0)
        except Exception as e:
            pass

print("[ERROR] 유효한 웹캠 프레임을 찾을 수 없습니다.")
sys.exit(1)
