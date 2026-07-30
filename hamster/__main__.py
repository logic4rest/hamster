"""
티처블 머신 손모양 인식으로 햄스터 봇 조종 (roboidai 방식)
- 가위 → 전진  (hamster.wheels(50, 50))
- 바위 → 후진  (hamster.wheels(-50, -50))
- 보   → 정지  (hamster.stop())
- 없음 → 정지 유지

사용 라이브러리:
  - roboidai : 카메라 + 티처블 머신 모델 (Keras 2.x 호환 내장)
  - roboid   : 햄스터 로봇 제어 (BLE 동글)
"""

from pathlib import Path

import roboidai as ai
from roboid import *

# ── 설정 ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_DIR    = str(PROJECT_ROOT / "models")  # roboidai는 폴더 경로를 받음

CONFIDENCE_THRESHOLD = 0.7   # 이 값 이상일 때만 인식 인정
WHEEL_SPEED          = 50    # 전진/후진 바퀴 속도 (-100 ~ 100)
COUNTDOWN_SEC        = 2     # 시작 전 카운트다운 초


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    # 1) 티처블 머신 모델 로드
    print(f"[INFO] 모델을 불러오는 중... ({MODEL_DIR})")
    tmi = ai.TmImage()
    tmi.load_model(MODEL_DIR)
    print("[INFO] 모델 로드 완료!")
    print(f"[INFO] 레이블: {tmi.get_all_labels()}")

    # 2) 햄스터 봇 연결 (BLE 동글)
    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()

    # 3) 카메라 열기 (내장 카메라)
    #    roboidai 카메라 ID: 'usb0' = OpenCV index 0 (기본 카메라)
    print("[INFO] 카메라를 시작합니다...")
    cam = ai.Camera('usb0', flip='h', square=True)
    cam.count_down(COUNTDOWN_SEC)

    print("[INFO] 손모양 인식 시작! ESC 키로 종료합니다.")
    print("        [가위] -> 전진")
    print("        [바위] -> 후진")
    print("        [보]   -> 정지")

    prev_label = None

    try:
        while True:
            # 4) 프레임 읽기
            image = cam.read()

            # 5) 손모양 인식
            if tmi.predict(image, CONFIDENCE_THRESHOLD):
                label = tmi.get_label()
                conf  = tmi.get_conf()

                # 레이블이 바뀔 때만 출력
                if label != prev_label:
                    print(f"[인식] {label}  (신뢰도: {conf:.0%})")
                    prev_label = label

                # 6) 햄스터 제어
                if label == "가위":
                    hamster.wheels(WHEEL_SPEED, WHEEL_SPEED)    # 전진
                elif label == "바위":
                    hamster.wheels(-WHEEL_SPEED, -WHEEL_SPEED)  # 후진
                elif label in ("보", "없음"):
                    hamster.stop()                               # 정지

            else:
                # 신뢰도 미달 → 안전하게 정지
                if prev_label is not None:
                    conf = tmi.get_conf()
                    print(f"[대기] 신뢰도 부족 ({conf:.0%}) → 정지")
                    prev_label = None
                hamster.stop()

            # 7) 화면 표시
            cam.show(image)

            # 8) ESC 키 종료
            if cam.check_key() == "esc":
                break

    finally:
        print("[INFO] 종료 중...")
        hamster.stop()


if __name__ == "__main__":
    main()
