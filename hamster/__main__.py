"""
티처블 머신 쓰레기 분리배출 햄스터 봇 제어 (v2.5)
================================================================================
- 무색 페트병 / 플라스틱 → 파란 LED (연속 4프레임 확정 + Beep)
- 캔                   → 초록 LED (연속 4프레임 확정 + Beep)
- 종이                 → 노란 LED (연속 4프레임 확정 + Beep)
- 종이팩 (우유팩)      → 하늘색(CYAN) LED (연속 4프레임 확정 + Beep)
- 이물질 / 라벨 / 유리병 → 빨간색 경고 LED (연속 4프레임 확정 + Beep)
- 없음 / 신뢰도 < 0.8   → 대기 (LED OFF)

스마트 신기능 (3, 4, 5번 + 경고 시스템):
  3. [자동 캡처]: 확정 순간 captures/ 폴더에 이미지 자동 저장
  4. [분리배출 팁]: 화면 하단에 분리배출 수칙 꿀팁 오버레이
  5. [실시간 통계]: 화면 우측 상단 수거 개수 통계 HUD & stats.json 저장

실행 방법:
    uv run hamster
    python -m hamster
"""

import json
import os
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import roboidai as ai
from roboid import *

# ── 설정 ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR    = str(PROJECT_ROOT / "models")
CAPTURES_DIR = PROJECT_ROOT / "captures"
STATS_PATH   = PROJECT_ROOT / "stats.json"

CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

CONFIDENCE_THRESHOLD = 0.8   # 이 값 미만이면 폐기/대기 (없음 처리)
REQUIRED_FRAMES      = 4     # 연속 4프레임 동일 시 최종 확정
COUNTDOWN_SEC        = 2     # 시작 전 카운트다운 초

# ── 카테고리 및 LED 매핑 ──────────────────────────────────────────────────────
CATEGORY_MAP = {
    "무색 페트병, 무색플라스틱": "플라스틱/페트병",
    "캔": "캔",
    "종이": "종이",
    "종이팩": "종이팩",
    "유리병, 유리통": "이물질/경고",
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
    "캔": ("green", "green"),
    "종이": ("yellow", "yellow"),
    "종이팩": ("cyan", "cyan"),
    "이물질/경고": ("red", "red"),
}

COLOR_BGR_MAP = {
    "플라스틱/페트병": (255, 50, 0),     # 파란색 (BGR)
    "캔": (0, 220, 0),                 # 초록색
    "종이": (0, 220, 255),               # 노란색
    "종이팩": (255, 235, 0),              # 하늘색
    "이물질/경고": (0, 0, 235),         # 빨간색 (경고 BGR)
    "없음": (120, 120, 120),             # 회색
}

# [기능 4] 올바른 분리배출 꿀팁 & 이물질 경고 안내문
RECYCLING_TIPS = {
    "플라스틱/페트병": "💡 TIP: 깨끗한 페트병입니다! 파란 수거함에 버려주세요.",
    "캔": "💡 TIP: 내용물을 비우고 헹군 뒤 차곡차곡 압착해 주세요!",
    "종이": "💡 TIP: 물기에 젖지 않게 펼쳐서 상자 테이프를 제거해 주세요!",
    "종이팩": "💡 TIP: 내용물을 비우고 물로 헹군 후 펼쳐서 말려주세요!",
    "이물질/경고": "⚠️ 경고: 페트병 안의 라벨, 얼음, 음식물 등 이물질을 제거해 주세요!",
    "없음": "💡 쓰레기를 카메라 중앙 화면에 비춰주세요.",
}


# ── 통계 관리 함수 (기능 5) ───────────────────────────────────────────────────
def load_stats() -> dict:
    """stats.json 파일에서 수거 통계 로드"""
    default_stats = {
        "플라스틱/페트병": 0,
        "캔": 0,
        "종이": 0,
        "종이팩": 0,
        "이물질/경고": 0,
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

    if "캔" in raw_label:
        return "캔"
    elif any(k in raw_label for k in ["이물질", "라벨", "음식물", "얼음", "유리병", "유리통", "병"]):
        return "이물질/경고"
    elif any(k in raw_label for k in ["페트병", "플라스틱"]):
        return "플라스틱/페트병"
    elif "종이팩" in raw_label or "우유팩" in raw_label:
        return "종이팩"
    elif "종이" in raw_label:
        return "종이"

    return "없음"


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
    stats_str = f"📊 총 {stats['total']}개 | 🔵플라스틱:{stats.get('플라스틱/페트병', 0)}  🟢캔:{stats.get('캔', 0)}  🟡종이:{stats.get('종이', 0)}  🩵종이팩:{stats.get('종이팩', 0)}  🔴경고:{stats.get('이물질/경고', 0)}"
    cv2.rectangle(frame, (0, 0), (w, 35), (20, 20, 20), -1)
    frame = put_korean_text(frame, stats_str, (10, 6), font_size=15, color_bgr=(255, 255, 255))

    return frame


def main():
    print(f"[INFO] 모델을 불러오는 중... ({MODEL_DIR})")
    tmi = ai.TmImage()
    tmi.load_model(MODEL_DIR)
    print("[INFO] 모델 로드 완료!")

    stats = load_stats()
    print(f"[INFO] 누적 분리배출 통계: {stats}")

    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()
    hamster.leds("off", "off")

    print("[INFO] 카메라를 시작합니다...")
    cam = ai.Camera('usb0', flip='h', square=True)
    cam.count_down(COUNTDOWN_SEC)

    print("\n" + "=" * 65)
    print("  [AI 쓰레기 분리배출 스마트 시스템 v2.5]")
    print("  - 깨끗한 플라스틱/페트병 -> 파란 LED (blue)")
    print("  - 캔                       -> 초록 LED (green)")
    print("  - 종이                     -> 노란 LED (yellow)")
    print("  - 종이팩                   -> 하늘색 LED (cyan)")
    print("  - 이물질 / 라벨 / 얼음     -> 빨간색 경고 LED (red)")
    print("  - 자동 캡처 & 꿀팁 자막 & 실시간 통계 HUD")
    print("  * 종료하려면 화면 창에서 ESC를 누르세요.")
    print("=" * 65 + "\n")

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
                mapped_category = map_raw_label_to_category(raw_label)

            if mapped_category != "없음":
                if mapped_category == current_target:
                    consecutive_count += 1
                else:
                    current_target = mapped_category
                    consecutive_count = 1

                image = draw_hud_and_bbox(image, mapped_category, conf, consecutive_count, REQUIRED_FRAMES, stats)

                # 4프레임 확정
                if consecutive_count >= REQUIRED_FRAMES:
                    print(f"\n[★ 확정 ★] 배출 안내: {mapped_category} (연속 {REQUIRED_FRAMES}프레임 감지!)")

                    # 통계 카운트 증가 & 저장
                    stats[mapped_category] = stats.get(mapped_category, 0) + 1
                    stats["total"] += 1
                    save_stats(stats)

                    # 확정 순간 자동 캡처
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    safe_cat = mapped_category.replace('/', '_')
                    cap_path = CAPTURES_DIR / f"{timestamp}_{safe_cat}.jpg"
                    cv2.imwrite(str(cap_path), image)
                    print(f"[자동 캡처 완료] 📷 {cap_path}")

                    # 로봇 알림: 삐 소리 + LED 켜기
                    left_led, right_led = LED_MAP.get(mapped_category, ("off", "off"))
                    hamster.beep()
                    hamster.leds(left_led, right_led)

                    start_time = time.time()
                    while time.time() - start_time < 2.0:
                        hamster.leds(left_led, right_led)
                        image = cam.read()
                        image = draw_hud_and_bbox(image, f"★ 확정: {mapped_category}", conf, REQUIRED_FRAMES, REQUIRED_FRAMES, stats)
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
                image = draw_hud_and_bbox(image, "없음", conf, 0, REQUIRED_FRAMES, stats)

            cam.show(image)

            if cam.check_key() == "esc":
                break

    finally:
        print("\n[INFO] 프로그램을 종료합니다.")
        hamster.leds("off", "off")
        hamster.stop()


if __name__ == "__main__":
    main()
