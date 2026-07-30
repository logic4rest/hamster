"""
티처블 머신 손모양 인식으로 햄스터 봇 조종
- 가위 → 전진
- 바위 → 후진
- 보   → 정지
- 없음 → 정지 유지

사용 라이브러리:
  - roboid  : 햄스터 로봇 제어 (BLE 동글)
  - tensorflow / keras : 티처블 머신 모델 로드
  - opencv  : 카메라 영상 처리
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

CONFIDENCE_THRESHOLD = 0.7   # 이 값 이상일 때만 인식 인정
WHEEL_SPEED          = 50    # 전진/후진 바퀴 속도 (-100 ~ 100)
COUNTDOWN_SEC        = 2     # 시작 전 카운트다운 초
IMG_SIZE             = 224   # 티처블 머신 기본 입력 크기

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
            cv2.imshow("Hamster Control", frame)
            if cv2.waitKey(30) & 0xFF == 27:  # ESC
                return


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    # 1) 모델·레이블 로드
    print("[INFO] 모델을 불러오는 중...")
    model  = load_model(MODEL_PATH)
    labels = load_labels(LABELS_PATH)
    print(f"[INFO] 레이블: {labels}")

    # 2) 햄스터 연결 (BLE 동글)
    print("[INFO] 햄스터 봇에 연결 중...")
    hamster = Hamster()

    # 3) 카메라 열기 (내장 카메라 = 인덱스 0)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] 카메라를 열 수 없습니다.")
        hamster.stop()
        return

    print(f"[INFO] {COUNTDOWN_SEC}초 후 시작합니다...")
    countdown(cap, COUNTDOWN_SEC)

    print("[INFO] 손모양 인식 시작! ESC 키로 종료합니다.")
    prev_label = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)   # 좌우 반전 (거울 모드)

            # 4) 추론
            input_data   = preprocess(frame)
            predictions  = model.predict(input_data, verbose=0)[0]
            best_idx     = int(np.argmax(predictions))
            confidence   = float(predictions[best_idx])
            label        = labels.get(best_idx, "알 수 없음")

            # 5) 햄스터 제어 (신뢰도 기준 이상일 때만)
            if confidence >= CONFIDENCE_THRESHOLD:
                if label != prev_label:
                    print(f"[인식] {label}  (신뢰도: {confidence:.2f})")
                    prev_label = label

                if label == "가위":
                    hamster.wheels(WHEEL_SPEED, WHEEL_SPEED)    # 전진
                elif label == "바위":
                    hamster.wheels(-WHEEL_SPEED, -WHEEL_SPEED)  # 후진
                elif label in ("보", "없음"):
                    hamster.stop()                               # 정지
            else:
                # 신뢰도 미달 → 안전하게 정지
                if prev_label is not None:
                    print(f"[대기] 신뢰도 부족 ({confidence:.2f}) → 정지")
                    prev_label = None
                hamster.stop()

            # 6) 화면 오버레이
            color = (0, 255, 0) if confidence >= CONFIDENCE_THRESHOLD else (0, 100, 255)
            cv2.putText(
                frame, f"{label}  {confidence:.0%}",
                (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3, cv2.LINE_AA,
            )

            action_map = {"가위": "FORWARD", "바위": "BACKWARD", "보": "STOP", "없음": "STOP"}
            action_text = action_map.get(label, "-") if confidence >= CONFIDENCE_THRESHOLD else "-"
            cv2.putText(
                frame, action_text,
                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA,
            )

            cv2.putText(
                frame, "ESC: Quit",
                (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (200, 200, 200), 1, cv2.LINE_AA,
            )
            cv2.imshow("Hamster Control", frame)

            # 7) 종료 (ESC)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    finally:
        print("[INFO] 종료 중...")
        hamster.stop()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
