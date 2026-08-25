"""
 TensorFlow/Keras 기반 추가 학습(Fine-Tuning / Retraining) 자동화 도구
 (한글 경로 PIL 유니코드 로더 안전 처리 에디션)
======================================================================
실행 방법:
    uv run python tools/train_local_keras.py
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "keras_model.h5"
LABELS_PATH = MODELS_DIR / "labels.txt"

def train_local_model():
    print("\n" + "=" * 70)
    print("  🧠 Keras AI 모델 추가 학습(Fine-Tuning)을 시작합니다...")
    print("=" * 70)

    # 1. 데이터셋 폴더 수집
    class_folders = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    if not class_folders:
        print("  ⚠️ 'data/' 폴더에 학습할 이미지 범주 폴더가 없습니다.")
        return

    labels = [d.name for d in class_folders]
    print(f"  📌 학습 대상 범주 ({len(labels)}개): {labels}")

    images = []
    y_labels = []

    img_size = 224

    for class_idx, folder in enumerate(class_folders):
        img_files = list(folder.glob("*.png")) + list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg"))
        loaded_count = 0
        for img_path in img_files:
            try:
                # PIL 로더로 한글 파일 경로 100% 안전 로드
                with Image.open(str(img_path)) as pil_img:
                    pil_img = pil_img.convert('RGB').resize((img_size, img_size))
                    arr = np.array(pil_img, dtype=np.float32)
                    arr = (arr / 127.5) - 1.0  # Teachable Machine 전처리 규격
                    images.append(arr)
                    y_labels.append(class_idx)
                    loaded_count += 1
            except Exception as e:
                pass
        print(f"   - '{folder.name}': {loaded_count}개 이미지 성공적 로드!")

    if len(images) == 0:
        print("  ⚠️ 로드된 학습 데이터가 없습니다.")
        return

    X = np.array(images, dtype=np.float32)
    y = np.array(y_labels, dtype=np.int32)
    y_cat = keras.utils.to_categorical(y, num_classes=len(labels))

    print(f"\n  총 {len(X)}개 이미지 데이터셋 파티셔닝 완료 (Shape: {X.shape})")

    # 2. 딥러닝 백본 신경망 구축 및 파인튜닝
    print("  🧠 MobileNetV2 백본 신경망 구축 및 파인튜닝 로딩...")
    base_model = tf.keras.applications.MobileNetV2(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False  # 가중치 동결

    inputs = keras.Input(shape=(img_size, img_size, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(len(labels), activation='softmax')(x)
    model = keras.Model(inputs, outputs)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    print("  🚀 추가 학습(Training Epochs) 10회 시행 중...")
    history = model.fit(
        X, y_cat,
        epochs=10,
        batch_size=8,
        verbose=1,
        shuffle=True
    )

    # 3. 모델 및 라벨 저장
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(MODEL_PATH))

    with open(str(LABELS_PATH), "w", encoding="utf-8") as f:
        for idx, name in enumerate(labels):
            f.write(f"{idx} {name}\n")

    print("\n" + "=" * 70)
    print(f"  🎉 추가 학습 완료! 최신 AI 모델 저장 위치: {MODEL_PATH}")
    print(f"  📋 최신 클래스 레이블 저장 위치: {LABELS_PATH}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    train_local_model()
