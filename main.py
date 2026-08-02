"""
티처블 머신 쓰레기 분리배출 햄스터 봇 제어 (OpenCV + Keras 직접 실행 방식 v2.5 이물질/경고 에디션)
================================================================================================
- 무색 페트병 / 플라스틱 → 파란 LED (연속 4프레임 확정 + Beep)
- 이물질 / 라벨 / 음식물 남음 → 빨간색 경고 LED (연속 4프레임 확정 + Beep)
- 종이                 → 노란 LED (연속 4프레임 확정 + Beep)
- 종이팩 (우유팩)      → 하늘색(CYAN) LED (연속 4프레임 확정 + Beep)
- 없음 / 신뢰도 < 0.8   → 대기 (LED OFF)

스마트 신기능 (3, 4, 5번 + 경고 시스템):
  3. [자동 캡처]: 확정 순간 captures/ 폴더에 이미지 자동 저장
  4. [분리배출 팁]: 화면 하단에 이물질 제거 경고 및 분리배출 꿀팁 오버레이
  5. [실시간 통계]: 화면 우측 상단 수거 개수 통계 HUD & stats.json 저장

실행 방법:
    python main.py
"""

import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from roboid import *

# ── 설정 ──────────────────────────────────────────────────────────────────────
MODEL_DIR   = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH  = os.path.join(MODEL_DIR, "keras_model.h5")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.txt")
CAPTURES_DIR = Path(__file__).parent / "captures"
STATS_PATH   = Path(__file__).parent / "stats.json"

CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

CONFIDENCE_THRESHOLD = 0.8   # 이 값 미만이면 폐기/대기 (없음 처리)
REQUIRED_FRAMES      = 4     # 연속 4프레임 동일 시 최종 확정
COUNTDOWN_SEC        = 2     # 시작 전 카운트다운 초
IMG_SIZE             = 224   # 티처블 머신 기본 입력 크기

# ── 카테고리 및 LED 매핑 ──────────────────────────────────────────────────────
CATEGORY_MAP = {
    "무색 페트병, 무색플라스틱": "플라스틱/페트병",
    "종이": "종이",
    "종이팩": "종이팩",
    "유리병, 유리통": "이물질/경고",
    "캔": "이물질/경고",
    "없음": "없음",
    # 하위 호환 및 이물질 관련 키워드
    "무색 페트병": "플라스틱/페트병",
    "플라스틱": "플라스틱/페트병",
    "이물질": "이물질/경고",
    "라벨": "이물질/경고",
    "음식물": "이물질/경고",
    "얼음": "이물질/경고",
    "병": "이물질/경고",
    "유리병": "이물질/경고",
    "종이팩(우유팩)": "종이팩",
}

LED_MAP = {
    "플라스틱/페트병": ("blue", "blue"),
    "이물질/경고": ("red", "red"),
    "종이": ("yellow", "yellow"),
    "종이팩": ("cyan", "cyan"),
}

COLOR_BGR_MAP = {
    "플라스틱/페트병": (255, 50, 0),     # 파란색 (BGR)
    "이물질/경고": (0, 0, 235),         # 빨간색 (경고 BGR)
    "종이": (0, 220, 255),               # 노란색
    "종이팩": (255, 235, 0),              # 하늘색
    "없음": (120, 120, 120),             # 회색
}

# [기능 4] 올바른 분리배출 꿀팁 & 이물질 경고 안내문
RECYCLING_TIPS = {
    "플라스틱/페트병": "💡 TIP: 깨끗한 페트병입니다! 파란 수거함에 버려주세요.",
    "이물질/경고": "⚠️ 경고: 페트병 안의 라벨, 얼음, 음식물 등 이물질을 제거해 주세요!",
    "종이": "💡 TIP: 물기에 젖지 않게 펼쳐서 상자 테이프를 제거해 주세요!",
    "종이팩": "💡 TIP: 내용물을 비우고 물로 헹군 후 펼쳐서 말려주세요!",
    "없음": "💡 쓰레기를 카메라 중앙 화면에 비춰주세요.",
}


# ── 통계 관리 함수 (기능 5) ───────────────────────────────────────────────────
def load_stats() -> dict:
    """stats.json 파일에서 수거 통계 로드"""
    default_stats = {
        "플라스틱/페트병": 0,
        "이물질/경고": 0,
        "종이": 0,
        "종이팩": 0,
        "total": 0,
    }
    if STATS_PATH.exists():
        try:
            with open(STATS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_stats.update(data)
        except Exception:
            pass
    return default_stats


def save_stats(stats: dict):
    """stats.json 파일에 통계 저장"""
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 통계 저장 실패: {e}")


# ── 한글 텍스트 렌더링 헬퍼 ───────────────────────────────────────────────────
def put_korean_text(frame: np.ndarray, text: str, xy: tuple, font_size: int = 20, color_bgr: tuple = (255, 255, 255)) -> np.ndarray:
    """OpenCV 프레임 위에 맑은 고딕 한글 텍스트 출력"""
    img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    try:
        font = ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    color_rgb = (color_bgr[2], color_bgr[1], color_bgr[0])
    draw.text(xy, text, font=font, fill=color_rgb)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def map_raw_label_to_category(raw_label: str) -> str:
    """학습 모델 원본 레이블 -> 통합 분리배출 카테고리 유연 매핑"""
    if not raw_label or raw_label == "없음":
        return "없음"

    if raw_label in CATEGORY_MAP:
        return CATEGORY_MAP[raw_label]

    if any(k in raw_label for k in ["이물질", "라벨", "음식물", "얼음", "유리병", "유리통", "병", "캔"]):
        return "이물질/경고"
    elif any(k in raw_label for k in ["페트병", "플라스틱"]):
        return "플라스틱/페트병"
    elif "종이팩" in raw_label or "우유팩" in raw_label:
        return "종이팩"
    elif "종이" in raw_label:
        return "종이"

    return "없음"


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


def draw_hud_and_bbox(frame: np.ndarray, category: str, conf: float, count: int, max_count: int, stats: dict) -> np.ndarray:
    """바운딩 박스 + 스마트 꿀팁 바 + 실시간 수거 통계 HUD 종합 오버레이"""
    h, w, _ = frame.shape
    clean_category = category.replace("★ 확정: ", "")
    color = COLOR_BGR_MAP.get(clean_category, (120, 120, 120))

    # 1) Bounding Box 사각형
    x1, y1 = int(w * 0.15), int(h * 0.15)
    x2, y2 = int(w * 0.85), int(h * 0.80)
    thickness = 3 if count < max_count else 5
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # 2) 모서리 포인터 선 (Corner Accents)
    c_len = int(min(w, h) * 0.06)
    cv2.line(frame, (x1, y1), (x1 + c_len, y1), color, thickness + 2)
    cv2.line(frame, (x1, y1), (x1, y1 + c_len), color, thickness + 2)
    cv2.line(frame, (x2, y1), (x2 - c_len, y1), color, thickness + 2)
    cv2.line(frame, (x2, y1), (x2, y1 + c_len), color, thickness + 2)
    cv2.line(frame, (x1, y2), (x1 + c_len, y2), color, thickness + 2)
    cv2.line(frame, (x1, y2), (x1, y2 - c_len), color, thickness + 2)
    cv2.line(frame, (x2, y2), (x2 - c_len, y2), color, thickness + 2)
    cv2.line(frame, (x2, y2), (x2, y2 - c_len), color, thickness + 2)

    # 3) 상단 중앙 카테고리 태그 바
    if clean_category != "없음":
        if category.startswith("★ 확정:"):
            tag_text = f"[확정] {clean_category}"
        else:
            tag_text = f"{clean_category} | {conf:.0%} [{count}/{max_count}]"
    else:
        tag_text = "쓰레기 감지 대기 중..."

    frame = put_korean_text(frame, tag_text, (x1 + 10, y1 - 32), font_size=18, color_bgr=color)

    # 4) [기능 4] 화면 하단 분리배출 꿀팁 & 경고 안내 바
    tip_text = RECYCLING_TIPS.get(clean_category, RECYCLING_TIPS["없음"])
    bar_color = (0, 0, 180) if clean_category == "이물질/경고" else (30, 30, 30)
    text_color = (255, 255, 255) if clean_category == "이물질/경고" else (0, 255, 255)
    cv2.rectangle(frame, (0, h - 45), (w, h), bar_color, -1)
    frame = put_korean_text(frame, tip_text, (15, h - 38), font_size=16, color_bgr=text_color)

    # 5) [기능 5] 우측 상단 실시간 수거 통계 HUD
    stats_str = f"📊 총 {stats['total']}개 | 🔵플라스틱:{stats.get('플라스틱/페트병', 0)}  🔴경고:{stats.get('이물질/경고', 0)}  🟡종이:{stats.get('종이', 0)}  🩵종이팩:{stats.get('종이팩', 0)}"
    cv2.rectangle(frame, (0, 0), (w, 35), (20, 20, 20), -1)
    frame = put_korean_text(frame, stats_str, (10, 6), font_size=15, color_bgr=(255, 255, 255))

    return frame


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

    stats = load_stats()
    print(f"[INFO] 누적 분리배출 통계: {stats}")

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

    print("\n" + "=" * 65)
    print("  [AI 쓰레기 분리배출 스마트 시스템 v2.5]")
    print("  - 깨끗한 플라스틱/페트병 -> 파란 LED (blue)")
    print("  - 이물질 / 라벨 / 음식물 -> 빨간색 경고 LED (red)")
    print("  - 종이                   -> 노란 LED (yellow)")
    print("  - 종이팩                 -> 하늘색 LED (cyan)")
    print("  - 자동 캡처 & 꿀팁 자막 & 실시간 통계 HUD")
    print("  * 종료하려면 화면 창에서 ESC를 누르세요.")
    print("=" * 65 + "\n")

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
                mapped_category = map_raw_label_to_category(raw_label)

            if mapped_category != "없음":
                if mapped_category == current_target:
                    consecutive_count += 1
                else:
                    current_target = mapped_category
                    consecutive_count = 1

                frame = draw_hud_and_bbox(frame, mapped_category, confidence, consecutive_count, REQUIRED_FRAMES, stats)

                if consecutive_count >= REQUIRED_FRAMES:
                    print(f"\n[★ 확정 ★] 배출 안내: {mapped_category} (연속 {REQUIRED_FRAMES}프레임 감지!)")

                    # [기능 5] 통계 카운트 증가 & 저장
                    stats[mapped_category] = stats.get(mapped_category, 0) + 1
                    stats["total"] += 1
                    save_stats(stats)

                    # [기능 3] 확정 순간 자동 캡처
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_cat = mapped_category.replace('/', '_')
                    cap_path = CAPTURES_DIR / f"{timestamp}_{safe_cat}.jpg"
                    cv2.imwrite(str(cap_path), frame)
                    print(f"[자동 캡처 완료] 📷 {cap_path}")

                    # 로봇 알림: 삐 소리 + LED 켜기
                    left_led, right_led = LED_MAP.get(mapped_category, ("off", "off"))
                    hamster.beep()
                    hamster.leds(left_led, right_led)

                    start_time = time.time()
                    while time.time() - start_time < 2.0:
                        hamster.leds(left_led, right_led)
                        ret, confirm_frame = cap.read()
                        if ret:
                            confirm_frame = cv2.flip(confirm_frame, 1)
                            confirm_frame = draw_hud_and_bbox(confirm_frame, f"★ 확정: {mapped_category}", confidence, REQUIRED_FRAMES, REQUIRED_FRAMES, stats)
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
                frame = draw_hud_and_bbox(frame, "없음", confidence, 0, REQUIRED_FRAMES, stats)

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
