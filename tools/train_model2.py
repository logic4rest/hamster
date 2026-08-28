"""
 🐹 햄스터 로봇 AI 모델 2 전용 대용량 데이터셋 재학습 (Retraining / Fine-Tuning) 스크립트
 =====================================================================================
 실행 방법:
     uv run python tools/train_model2.py
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image

# 윈도우 콘솔 UTF-8 안전 인코딩
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import tensorflow as tf
import tf_keras as keras
from tf_keras import layers

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CAPTURES_DIR = PROJECT_ROOT / "captures"
MODEL2_DIR = PROJECT_ROOT / "models" / "모델2"
MODEL2_PATH = MODEL2_DIR / "keras_model.h5"
LABELS2_PATH = MODEL2_DIR / "labels.txt"

# 표준 카테고리 매핑 함수
def map_folder_to_class(folder_name: str) -> str:
    name = folder_name.strip()
    if "종이팩" in name or "우유팩" in name:
        return "종이팩"
    elif "종이" in name:
        return "종이"
    elif "캔" in name:
        return "캔"
    elif "페트병" in name or "플라스틱" in name:
        return "플라스틱&페트병"
    elif "병" in name or "유리" in name:
        return "유리병"
    elif "없음" in name or "대기" in name:
        return "없음"
    return name

def train_model2():
    print("\n" + "=" * 75)
    print("  🧠 [모델2 재학습 엔진] data/ 및 captures/ 데이터 수집 & AI 모델 재학습 시작")
    print("=" * 75)

    # 1. data/ 및 captures/ 폴더 이미지 수집
    class_dataset = {}

    # data/ 폴더 처리
    if DATA_DIR.exists():
        for sub_dir in DATA_DIR.iterdir():
            if sub_dir.is_dir():
                target_cls = map_folder_to_class(sub_dir.name)
                if target_cls not in class_dataset:
                    class_dataset[target_cls] = []
                
                img_files = list(sub_dir.glob("*.png")) + list(sub_dir.glob("*.jpg")) + list(sub_dir.glob("*.jpeg"))
                class_dataset[target_cls].extend(img_files)

    # captures/ 내의 서브디렉토리 및 파일 처리
    if CAPTURES_DIR.exists():
        for cap_file in CAPTURES_DIR.glob("**/*.*"):
            if cap_file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                stem = cap_file.stem
                matched_cls = None
                if "종이팩" in stem:
                    matched_cls = "종이팩"
                elif "종이" in stem:
                    matched_cls = "종이"
                elif "캔" in stem:
                    matched_cls = "캔"
                elif "플라스틱" in stem or "페트병" in stem:
                    matched_cls = "플라스틱&페트병"
                elif "유리" in stem or "병" in stem:
                    matched_cls = "유리병"
                elif "없음" in stem:
                    matched_cls = "없음"

                if matched_cls:
                    if matched_cls not in class_dataset:
                        class_dataset[matched_cls] = []
                    class_dataset[matched_cls].append(cap_file)

    sorted_classes = sorted(list(class_dataset.keys()))
    print(f"  📌 학습 범주 목록 ({len(sorted_classes)}개): {sorted_classes}")

    images = []
    y_labels = []
    img_size = 224

    for class_idx, class_name in enumerate(sorted_classes):
        file_list = class_dataset[class_name]
        loaded_count = 0
        for img_path in file_list:
            try:
                with Image.open(str(img_path)) as pil_img:
                    pil_img = pil_img.convert('RGB').resize((img_size, img_size))
                    arr = np.array(pil_img, dtype=np.float32)
                    arr = (arr / 127.5) - 1.0  # Teachable Machine 규격 전처리 [-1, 1]
                    images.append(arr)
                    y_labels.append(class_idx)
                    loaded_count += 1
            except Exception:
                pass
        print(f"   - '{class_name}': {loaded_count}개 이미지 로드 완료")

    if len(images) == 0:
        print("  ⚠️ 학습할 이미지를 찾지 못했습니다.")
        return

    X = np.array(images, dtype=np.float32)
    y = np.array(y_labels, dtype=np.int32)
    y_cat = keras.utils.to_categorical(y, num_classes=len(sorted_classes))

    print(f"\n  총 {len(X)}개 이미지 전처리 및 넘파이 파티셔닝 완료 (Shape: {X.shape})")

    # 2. 데이터 증강 (Data Augmentation) 파이프라인
    data_augmentation = keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.15),
        layers.RandomZoom(0.15),
        layers.RandomTranslation(0.1, 0.1),
    ])

    # 3. MobileNetV2 백본 파인튜닝 전이학습 모델 구축
    print("\n  🧠 MobileNetV2 백본 신경망 구축 및 데이터 증강 파이프라인 결합...")
    base_model = keras.applications.MobileNetV2(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False  # 사전 학습 가중치 동결

    inputs = layers.Input(shape=(img_size, img_size, 3))
    x = data_augmentation(inputs)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(len(sorted_classes), activation='softmax')(x)
    model = keras.Model(inputs, outputs)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    print("  🚀 [1단계 학습] 백본 동결 파인튜닝 (Epochs 12회)...")
    model.fit(
        X, y_cat,
        epochs=12,
        batch_size=8,
        verbose=1,
        shuffle=True
    )

    print("\n  🚀 [2단계 미세조정] 상위 레이어 언동결 미세 파인튜닝 (Epochs 8회)...")
    base_model.trainable = True
    # MobileNetV2 상위 30개 레이어만 미세조정
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    model.fit(
        X, y_cat,
        epochs=8,
        batch_size=8,
        verbose=1,
        shuffle=True
    )

    # 4. 모델2 저장
    MODEL2_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(MODEL2_PATH))

    with open(str(LABELS2_PATH), "w", encoding="utf-8") as f:
        for idx, name in enumerate(sorted_classes):
            f.write(f"{idx} {name}\n")

    print("\n" + "=" * 75)
    print(f"  🎉 [모델2 재학습 완수!] 최신 Keras 모델 저장: {MODEL2_PATH}")
    print(f"  📋 최신 클래스 레이블 저장: {LABELS2_PATH}")
    print(f"  🏷️ 학습 완료 클래스: {sorted_classes}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    train_model2()
