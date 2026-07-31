"""
티처블 머신 쓰레기 분리배출 햄스터 봇 제어 (OpenCV + Keras 직접 실행 방식 + 바운딩 박스)
================================================================================
- 무색 페트병 / 플라스틱 → 파란 LED (연속 4프레임 확정 + Beep)
- 캔                   → 초록 LED (연속 4프레임 확정 + Beep)
- 종이                 → 노란 LED (연속 4프레임 확정 + Beep)
- 병 (유리병)          → 빨간 LED (연속 4프레임 확정 + Beep)
- 종이팩 (우유팩)      → 하늘색(CYAN) LED (연속 4프레임 확정 + Beep)
- 없음 / 신뢰도 < 0.8   → 대기 (LED OFF)

실행 방법:
    python main.py
"""

import os
import time

import cv2
import numpy as np
from roboid import *

# ── 설정 ──────────────────────────────────────────────────────────────────────
MODEL_DIR   = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH  = os.path.join(MODEL_DIR, "keras_model.h5")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.txt")

CONFIDENCE_THRESHOLD = 0.8   # 이 값 미만이면 폐기/대기 (없음 처리)
REQUIRED_FRAMES      = 4     # 연속 4프레임 동일 시 최종 확정
COUNTDOWN_SEC        = 2     # 시작 전 카운트다운 초
IMG_SIZE             = 224   # 티처블 머신 기본 입력 크기

# ── 카테고리 및 LED 매핑 ──────────────────────────────────────────────────────
CATEGORY_MAP = {
    "무색 페트병": "플라스틱/페트병",
    "플라스틱": "플라스틱/페트병",
    "캔": "캔",
    "종이": "종이",
    "병": "병(유리병)",
    "종이팩(우유팩)": "종이팩",
    "없음": "없음",
}

# 햄스터 로봇 LED 색상 매핑
LED_MAP = {
    "플라스틱/페트병": ("blue", "blue"),
    "캔": ("green", "green"),
    "종이": ("yellow", "yellow"),
    "병(유리병)": ("red", "red"),
    "종이팩": ("cyan", "cyan"),
}

# 화면 오버레이 BGR 색상 매핑
COLOR_BGR_MAP = {
    "플라스틱/페트병": (255, 50, 0),     # 파란색 (BGR)
    "캔": (0, 220, 0),                 # 초록색
    "종이": (0, 220, 255),               # 노란색
    "병(유리병)": (0, 0, 235),            # 빨간색
    "종이팩": (255, 235, 0),              # 하늘색
    "없음": (120, 120, 120),             # 회색
}


# ── 라벨 로드 ─────────────────────────────────────────────────────────────────
def load_labels(path: str) -> dict[int, str]:
    """labels.txt 파싱 → {인덱스: 레이블} 딕셔너리 반환"""
    labels = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, name = line.split(" ", 1)
            labels[int(idx)] = name
    return labels


# ── 모델 로드 ─────────────────────────────────────────────────────────────────
def load_model(path: str):
    """Keras 모델 로드 — Teachable Machine 구버전 .h5 모델 호환 로더"""
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


# ── 이미지 전처리 ──────────────────────────────────────────────────────────────
def preprocess(frame: np.ndarray) -> np.ndarray:
    """OpenCV BGR 프레임 → 티처블 머신 입력 형식 변환"""
    img = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)
    img = (img / 127.5) - 1.0              # [-1, 1] 정규화
    return np.expand_dims(img, axis=0)     # (1, 224, 224, 3)


# ── Bounding Box 시각화 ───────────────────────────────────────────────────────
def draw_bbox(frame: np.ndarray, category: str, conf: float, count: int, max_count: int):
    """카메라 화면상에 바운딩 박스(Bounding Box) 오버레이 시각화"""
    h, w, _ = frame.shape
    x1, y1 = int(w * 0.15), int(h * 0.15)
    x2, y2 = int(w * 0.85), int(h * 0.85)

    clean_category = category.replace("★ 확정: ", "")
    color = COLOR_BGR_MAP.get(clean_category, (120, 120, 120))
    thickness = 3 if count < max_count else 5

    # 1) 메인 Bounding Box 사각형
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # 2) 모서리 포인터 선 (Corner Accents)
    c_len = int(min(w, h) * 0.06)
    # Top-Left
    cv2.line(frame, (x1, y1), (x1 + c_len, y1), color, thickness + 2)
    cv2.line(frame, (x1, y1), (x1, y1 + c_len), color, thickness + 2)
    # Top-Right
    cv2.line(frame, (x2, y1), (x2 - c_len, y1), color, thickness + 2)
    cv2.line(frame, (x2, y1), (x2, y1 + c_len), color, thickness + 2)
    # Bottom-Left
    cv2.line(frame, (x1, y2), (x1 + c_len, y2), color, thickness + 2)
    cv2.line(frame, (x1, y2), (x1, y1 + c_len), color, thickness + 2)
    # Bottom-Right
    cv2.line(frame, (x2, y2), (x2 - c_len, y2), color, thickness + 2)
    cv2.line(frame, (x2, y2), (x2, y2 - c_len), color, thickness + 2)

    # 3) 상단 레이블 태그 바
    if clean_category != "없음":
        if category.startswith("★ 확정:"):
            tag_text = f" [확정] {clean_category} "
        else:
            tag_text = f" {clean_category} | {conf:.0%} [{count}/{max_count}] "
    else:
        tag_text = " 쓰레기 감지 대기 중... "

    (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    cv2.rectangle(frame, (x1, y1 - th - 14), (x1 + tw + 10, y1), color, -1)
    cv2.putText(frame, tag_text, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)


# ── 카운트다운 ────────────────────────────────────────────────────────────────
def countdown(cap: cv2.VideoCapture, seconds: int):
    """카메라 화면 위에 카운트다운을 표시한다."""
    for i in range(seconds, 0, -1):
        deadline = time.time() + 1.0
        while time.time() < deadline:
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            cv2.putText(
                frame, str(i),
                (frame.shape[1] // 2 - 40, frame.shape[0] // 2 + 40),
                cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 0), 6, cv2.LINE_AA,
            )
            cv2.imshow("Waste Sorting Hamster", frame)
            if cv2.waitKey(30) & 0xFF == 27:  # ESC
                return


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    print("[INFO] 모델을 불러오는 중...")
    model  = load_model(MODEL_PATH)
    labels = load_labels(LABELS_PATH)
    print(f"[INFO] 레이블: {labels}")

    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()
    hamster.leds("off", "off")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] 카메라를 열 수 없습니다.")
        hamster.stop()
        return

    print(f"[INFO] {COUNTDOWN_SEC}초 후 시작합니다...")
    countdown(cap, COUNTDOWN_SEC)

    print("\n" + "=" * 60)
    print("  [쓰레기 분리배출 스마트 감지 시스템]")
    print("  - 플라스틱 / 무색 페트병 -> 파란 LED (blue)")
    print("  - 캔                    -> 초록 LED (green)")
    print("  - 종이                  -> 노란 LED (yellow)")
    print("  - 병(유리병)            -> 빨간 LED (red)")
    print("  - 종이팩                -> 하늘색 LED (cyan)")
    print("  - 연속 4프레임 감지 시 배출 안내 확정")
    print("  * 종료하려면 화면 창에서 ESC를 누르세요.")
    print("=" * 60 + "\n")

    current_target = None
    consecutive_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)   # 거울 모드

            input_data   = preprocess(frame)
            predictions  = model.predict(input_data, verbose=0)[0]
            best_idx     = int(np.argmax(predictions))
            confidence   = float(predictions[best_idx])
            raw_label    = labels.get(best_idx, "알 수 없음")

            if confidence < CONFIDENCE_THRESHOLD:
                mapped_category = "없음"
            else:
                mapped_category = CATEGORY_MAP.get(raw_label, "없음")

            if mapped_category != "없음":
                if mapped_category == current_target:
                    consecutive_count += 1
                else:
                    current_target = mapped_category
                    consecutive_count = 1

                # 바운딩 박스 시각화
                draw_bbox(frame, mapped_category, confidence, consecutive_count, REQUIRED_FRAMES)

                if consecutive_count >= REQUIRED_FRAMES:
                    print(f"\n[★ 확정 ★] 배출 안내: {mapped_category} (연속 {REQUIRED_FRAMES}프레임 감지!)")
                    left_led, right_led = LED_MAP.get(mapped_category, ("off", "off"))

                    # 로봇 알림: 삐 소리 + LED 켜기
                    hamster.beep()
                    hamster.leds(left_led, right_led)

                    start_time = time.time()
                    while time.time() - start_time < 2.0:
                        hamster.leds(left_led, right_led)
                        ret, confirm_frame = cap.read()
                        if ret:
                            confirm_frame = cv2.flip(confirm_frame, 1)
                            draw_bbox(confirm_frame, f"★ 확정: {mapped_category}", confidence, REQUIRED_FRAMES, REQUIRED_FRAMES)
                            cv2.imshow("Waste Sorting Hamster", confirm_frame)
                        if cv2.waitKey(30) & 0xFF == 27:
                            return

                    hamster.leds("off", "off")
                    current_target = None
                    consecutive_count = 0
                    print("[대기] 다음 쓰레기 감지 대기 중...\n")

            else:
                current_target = None
                consecutive_count = 0
                hamster.leds("off", "off")
                draw_bbox(frame, "없음", confidence, 0, REQUIRED_FRAMES)

            cv2.imshow("Waste Sorting Hamster", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

    finally:
        print("\n[INFO] 종료 중...")
        hamster.leds("off", "off")
        hamster.stop()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
