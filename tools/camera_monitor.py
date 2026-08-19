"""
웹캠 AI 쓰레기 감지 실시간 모니터링 모니터 창 (v1.0)
====================================================================================================
- 캡처가 아닌 30~60 FPS 실시간 라이브 영상 뷰어 프로그램
- 카메라 화면에 Teachable Machine AI 인식 클래스, 신뢰도 %, 4종 카테고리 바운딩 박스 실시간 표시
- 햄스터 로봇 연결 없이 독립 실행 가능

실행 방법:
    python tools/camera_monitor.py
    uv run python tools/camera_monitor.py
"""

import os
import sys
import time
from pathlib import Path

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODEL_DIR   = PROJECT_ROOT / "models"
MODEL_PATH  = MODEL_DIR / "keras_model.h5"
LABELS_PATH = MODEL_DIR / "labels.txt"
STATS_PATH  = PROJECT_ROOT / "stats.json"

IMG_SIZE = 224
CONFIDENCE_THRESHOLD = 0.8
REQUIRED_FRAMES = 4

# ── 카테고리 및 BGR 색상 매핑 ──────────────────────────────────────────────
CATEGORY_MAP = {
    "무색 페트병, 무색플라스틱": "플라스틱/페트병",
    "플라스틱": "플라스틱/페트병",
    "무색 페트병": "플라스틱/페트병",
    "패트병": "플라스틱/페트병",
    "유리병, 유리통": "플라스틱/페트병",
    "유리병": "플라스틱/페트병",
    "유리통": "플라스틱/페트병",
    "병": "플라스틱/페트병",
    "캔": "캔",
    "종이": "종이",
    "종이팩": "종이팩",
    "종이팩(우유팩)": "종이팩",
    "이물질": "이물질/경고",
    "라벨": "이물질/경고",
    "음식물": "이물질/경고",
    "얼음": "이물질/경고",
    "없음": "없음",
}

COLOR_BGR_MAP = {
    "플라스틱/페트병": (255, 50, 0),     # 파란색
    "캔": (0, 220, 0),                 # 초록색
    "종이": (0, 220, 255),               # 노란색
    "종이팩": (255, 255, 255),            # 흰색
    "이물질/경고": (0, 0, 235),         # 빨간색
    "없음": (120, 120, 120),             # 회색
}


def load_labels(path: Path) -> dict:
    labels = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, name = line.split(" ", 1)
            labels[int(idx)] = name
    return labels


def load_model(path: Path):
    try:
        import tf_keras
        return tf_keras.models.load_model(str(path), compile=False)
    except ImportError:
        pass

    from tensorflow import keras
    _orig_init = keras.layers.DepthwiseConv2D.__init__

    def _patched_init(self, *args, **kwargs):
        kwargs.pop("groups", None)
        _orig_init(self, *args, **kwargs)

    keras.layers.DepthwiseConv2D.__init__ = _patched_init
    return keras.models.load_model(str(path), compile=False)


def preprocess(frame: np.ndarray) -> np.ndarray:
    img = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)
    img = (img / 127.5) - 1.0
    return np.expand_dims(img, axis=0)


def map_raw_label_to_category(raw_label: str) -> str:
    if not raw_label or raw_label == "없음":
        return "없음"
    if raw_label in CATEGORY_MAP:
        return CATEGORY_MAP[raw_label]
    if any(k in raw_label for k in ["유리", "병", "페트병", "패트병", "플라스틱"]):
        return "플라스틱/페트병"
    elif "캔" in raw_label:
        return "캔"
    elif any(k in raw_label for k in ["이물질", "라벨", "음식물", "얼음"]):
        return "이물질/경고"
    elif "종이팩" in raw_label or "우유팩" in raw_label:
        return "종이팩"
    elif "종이" in raw_label:
        return "종이"
    return "없음"


def render_live_hud(frame: np.ndarray, category: str, conf: float, count: int, raw_label: str, fps: float) -> np.ndarray:
    """실시간 모니터링 단일 패스 HUD 렌더러"""
    if frame is None:
        return frame

    canvas = frame.copy()
    h, w, _ = canvas.shape
    color = COLOR_BGR_MAP.get(category, (120, 120, 120))

    # 1. Bounding Box 사각형 및 모서리 포인터
    x1, y1 = int(w * 0.15), int(h * 0.15)
    x2, y2 = int(w * 0.85), int(h * 0.80)
    thickness = 4 if count >= REQUIRED_FRAMES else 2
    cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

    c_len = int(min(w, h) * 0.08)
    cv2.line(canvas, (x1, y1), (x1 + c_len, y1), color, thickness + 2)
    cv2.line(canvas, (x1, y1), (x1, y1 + c_len), color, thickness + 2)
    cv2.line(canvas, (x2, y1), (x2 - c_len, y1), color, thickness + 2)
    cv2.line(canvas, (x2, y1), (x2, y1 + c_len), color, thickness + 2)
    cv2.line(canvas, (x1, y2), (x1 + c_len, y2), color, thickness + 2)
    cv2.line(canvas, (x1, y2), (x1, y2 - c_len), color, thickness + 2)
    cv2.line(canvas, (x2, y2), (x2 - c_len, y2), color, thickness + 2)
    cv2.line(canvas, (x2, y2), (x2, y2 - c_len), color, thickness + 2)

    # 2. 신뢰도 게이지 바
    gauge_w = int((x2 - x1) * min(conf, 1.0))
    cv2.rectangle(canvas, (x1, y2 + 10), (x1 + gauge_w, y2 + 25), color, -1)
    cv2.rectangle(canvas, (x1, y2 + 10), (x2, y2 + 25), (100, 100, 100), 2)

    # 3. 텍스트 라벨 목록 준비
    text_list = []

    # 상단 메인 라벨
    if category != "없음":
        tag_text = f"★ [인식 확정] {category} (신뢰도: {conf:.1%}) [{count}/{REQUIRED_FRAMES}]" if count >= REQUIRED_FRAMES else f"[{category}] 신뢰도: {conf:.1%} [{count}/{REQUIRED_FRAMES}]"
    else:
        tag_text = f"쓰레기를 중앙 사각형 안에 올려놓아 주세요. (원본: {raw_label})"

    text_list.append((tag_text, (x1 + 10, y1 - 35), 18, color))

    # 하단 상태 바
    if count >= REQUIRED_FRAMES:
        status_text = f"✅ 배출 대상 확정! 로봇 2초 LED 점등 & 수거함 이동 모션 발동 조건 충족!"
        bar_bg = (0, 180, 0)
    else:
        status_text = f"🔍 탐색 중... (동일 분류 {REQUIRED_FRAMES}프레임 연속 유지 시 확정)"
        bar_bg = (40, 40, 40)

    cv2.rectangle(canvas, (0, h - 45), (w, h), bar_bg, -1)
    text_list.append((status_text, (15, h - 38), 15, (255, 255, 255)))

    # 상단 FPS 및 모니터링 바
    top_bar_text = f"📹 [실시간 라이브 AI 카메라 모니터] {fps:.1f} FPS | Q 또는 ESC 종료"
    cv2.rectangle(canvas, (0, 0), (w, 35), (20, 20, 20), -1)
    text_list.append((top_bar_text, (15, 6), 14, (0, 255, 255)))

    # 4. 단 한 번의 PIL 고속 변환
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img_pil)

    try:
        font_cache = {
            14: ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 14),
            15: ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 15),
            18: ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 18),
        }
    except Exception:
        font_cache = {}

    for text, xy, size, color_bgr in text_list:
        font = font_cache.get(size, ImageFont.load_default())
        color_rgb = (int(color_bgr[2]), int(color_bgr[1]), int(color_bgr[0]))
        draw.text(xy, text, font=font, fill=color_rgb)

    res_rgb = np.array(img_pil)
    return cv2.cvtColor(res_rgb, cv2.COLOR_RGB2BGR)


def open_live_camera():
    print("[INFO] 웹캠 카메라를 연결하는 중...")
    for idx in [0, 1, 2, 3]:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"[INFO] 카메라 연결 성공! (인덱스: {idx}, DirectShow 모드)")
                return cap

        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"[INFO] 카메라 연결 성공! (인덱스: {idx})")
                return cap

    return None


def main():
    print("\n" + "=" * 65)
    print("  📹 [실시간 라이브 카메라 AI 감지 모니터링 프로그램]")
    print("  - 실시간 카메라 영상에 쓰레기 인식 및 Bounding Box 고속 렌더링")
    print("  - 햄스터 로봇 연결 없이 카메라 인식 테스트 가능")
    print("  * 종료하려면 화면 창에서 ESC 또는 Q를 누르세요.")
    print("=" * 65 + "\n")

    print("[INFO] Teachable Machine AI 모델 로드 중...")
    model = load_model(MODEL_PATH)
    labels = load_labels(LABELS_PATH)
    print("[INFO] 모델 로드 완료!")

    cap = open_live_camera()
    if cap is None:
        print("[ERROR] 웹캠 카메라를 열 수 없습니다!")
        return

    current_target = None
    consecutive_count = 0
    prev_time = time.time()
    fps = 30.0

    cv2.namedWindow("Live AI Waste Monitor", cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # 좌우 반전 (거울 모드)
            frame = cv2.flip(frame, 1)

            # FPS 계산
            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 0.001)
            prev_time = curr_time

            # AI 모델 추론
            input_data = preprocess(frame)
            predictions = model.predict(input_data, verbose=0)[0]
            best_idx = int(np.argmax(predictions))
            confidence = float(predictions[best_idx])
            raw_label = labels.get(best_idx, "없음")

            if confidence < CONFIDENCE_THRESHOLD:
                mapped_category = "없음"
            else:
                mapped_category = map_raw_label_to_category(raw_label)

            if mapped_category != "없음":
                if mapped_category == current_target:
                    consecutive_count += 1
                else:
                    current_target = mapped_category
                    consecutive_count = 1
            else:
                current_target = None
                consecutive_count = 0

            display_frame = render_live_hud(frame, mapped_category, confidence, consecutive_count, raw_label, fps)
            cv2.imshow("Live AI Waste Monitor", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in [27, ord('q'), ord('Q')]:
                print("\n[INFO] 모니터링 프로그램을 종료합니다.")
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
