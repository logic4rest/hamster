import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(r"c:\Users\User\Desktop\hamster")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import load_model, load_labels, preprocess, map_raw_label_to_category, draw_hud_and_bbox, load_stats

brain_dir = Path(r"C:\Users\User\.gemini\antigravity\brain\11ff0cde-0f06-4ef3-876e-c9ee53f4423f")
live_path = brain_dir / "webcam_live.jpg"
out_path = brain_dir / "ai_recognition_preview.jpg"

if not live_path.exists():
    print("[ERROR] webcam_live.jpg 없음")
    sys.exit(1)

frame = cv2.imread(str(live_path))
if frame is None:
    print("[ERROR] 이미지 읽기 실패")
    sys.exit(1)

model_path = PROJECT_ROOT / "models" / "keras_model.h5"
labels_path = PROJECT_ROOT / "models" / "labels.txt"

model = load_model(str(model_path))
labels = load_labels(str(labels_path))
stats = load_stats()

input_data = preprocess(frame)
predictions = model.predict(input_data, verbose=0)[0]
best_idx = int(np.argmax(predictions))
confidence = float(predictions[best_idx])
raw_label = labels.get(best_idx, "없음")

category = map_raw_label_to_category(raw_label)

print(f"[AI 감지 결과] 원본 레이블: '{raw_label}' ➔ 카테고리: '{category}' (신뢰도: {confidence:.1%})")

# HUD & Bounding Box 주입
annotated_frame = draw_hud_and_bbox(frame, category, confidence, 4, 4, stats)
cv2.imwrite(str(out_path), annotated_frame)
print(f"[OK] 주석 처리된 AI 화면 저장 완료: {out_path}")
