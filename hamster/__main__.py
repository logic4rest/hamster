"""
티처블 머신 쓰레기 분리배출 햄스터 봇 제어 (roboidai 방식 + 바운딩 박스 오버레이)
=============================================================================
- 무색 페트병 / 플라스틱 → 파란 LED (연속 2프레임 확정 + Beep)
- 캔                   → 초록 LED (연속 2프레임 확정 + Beep)
- 종이                 → 노란 LED (연속 2프레임 확정 + Beep)
- 병 (유리병)          → 빨간 LED (연속 2프레임 확정 + Beep)
- 종이팩 (우유팩)      → 하늘색(CYAN) LED (연속 2프레임 확정 + Beep)
- 없음 / 신뢰도 < 0.8   → 대기 (LED OFF)

실행 방법:
    uv run hamster
    python -m hamster
"""

import time
from pathlib import Path

import cv2
import roboidai as ai
from roboid import *

# ── 설정 ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR    = str(PROJECT_ROOT / "models")

CONFIDENCE_THRESHOLD = 0.8   # 이 값 미만이면 폐기/대기 (없음 처리)
REQUIRED_FRAMES      = 2     # 연속 2프레임 동일 시 최종 확정
COUNTDOWN_SEC        = 2     # 시작 전 카운트다운 초

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


def draw_bbox(frame, category, conf, count, max_count):
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


def main():
    print(f"[INFO] 모델을 불러오는 중... ({MODEL_DIR})")
    tmi = ai.TmImage()
    tmi.load_model(MODEL_DIR)
    print("[INFO] 모델 로드 완료!")
    print(f"[INFO] 원본 레이블: {tmi.get_all_labels()}")

    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()
    hamster.leds("off", "off")

    print("[INFO] 카메라를 시작합니다...")
    cam = ai.Camera('usb0', flip='h', square=True)
    cam.count_down(COUNTDOWN_SEC)

    print("\n" + "=" * 60)
    print("  [쓰레기 분리배출 스마트 감지 시스템]")
    print("  - 플라스틱 / 무색 페트병 -> 파란 LED (blue)")
    print("  - 캔                    -> 초록 LED (green)")
    print("  - 종이                  -> 노란 LED (yellow)")
    print("  - 병(유리병)            -> 빨간 LED (red)")
    print("  - 종이팩                -> 하늘색 LED (cyan)")
    print("  - 연속 2프레임 감지 시 배출 안내 확정")
    print("  * 종료하려면 화면 창에서 ESC를 누르세요.")
    print("=" * 60 + "\n")

    current_target = None
    consecutive_count = 0

    try:
        while True:
            image = cam.read()

            tmi.predict(image, 0.0)
            raw_label = tmi.get_label()
            conf = tmi.get_conf()

            if conf < CONFIDENCE_THRESHOLD:
                mapped_category = "없음"
            else:
                mapped_category = CATEGORY_MAP.get(raw_label, "없음")

            if mapped_category != "없음":
                if mapped_category == current_target:
                    consecutive_count += 1
                else:
                    current_target = mapped_category
                    consecutive_count = 1

                # 바운딩 박스 화면 오버레이
                draw_bbox(image, mapped_category, conf, consecutive_count, REQUIRED_FRAMES)

                if consecutive_count >= REQUIRED_FRAMES:
                    print(f"\n[★ 확정 ★] 배출 안내: {mapped_category} (연속 {REQUIRED_FRAMES}프레임 감지!)")
                    left_led, right_led = LED_MAP.get(mapped_category, ("off", "off"))

                    # 로봇 알림: 삐 소리 + LED 켜기
                    hamster.beep()
                    hamster.leds(left_led, right_led)

                    start_time = time.time()
                    while time.time() - start_time < 2.0:
                        hamster.leds(left_led, right_led)
                        image = cam.read()
                        draw_bbox(image, f"★ 확정: {mapped_category}", conf, REQUIRED_FRAMES, REQUIRED_FRAMES)
                        cam.show(image)
                        if cam.check_key() == "esc":
                            return

                    hamster.leds("off", "off")
                    current_target = None
                    consecutive_count = 0
                    print("[대기] 다음 쓰레기 감지 대기 중...\n")
            else:
                current_target = None
                consecutive_count = 0
                hamster.leds("off", "off")
                draw_bbox(image, "없음", conf, 0, REQUIRED_FRAMES)

            cam.show(image)

            if cam.check_key() == "esc":
                break

    finally:
        print("\n[INFO] 프로그램을 종료합니다.")
        hamster.leds("off", "off")
        hamster.stop()


if __name__ == "__main__":
    main()
