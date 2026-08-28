"""
 🐹 햄스터 로봇 모델1 & 모델2 고밀도 정밀 재학습 (High-Precision Retraining) 도구
 ===============================================================================
 종이(Paper)와 캔(Can)의 오인식을 100% 방지하기 위한 데이터 통합 및 딥러닝 재학습 스크립트
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image

# 윈도우 콘솔 UTF-8 인코딩 안전 처리
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

MODEL1_DIR = PROJECT_ROOT / "models" / "모델1"
MODEL2_DIR = PROJECT_ROOT / "models" / "모델2"

def collect_dataset(include_none: bool = True):
    """data/ 및 captures/ 디렉토리 전수 조사 및 데이터 수집"""
    class_dataset = {}

    def add_image(cls_name: str, img_path: Path):
        if cls_name not in class_dataset:
            class_dataset[cls_name] = []
        class_dataset[cls_name].append(img_path)

    # 1. data/ 폴더 스캔
    if DATA_DIR.exists():
        for sub_dir in DATA_DIR.iterdir():
            if sub_dir.is_dir():
                name = sub_dir.name.strip()
                target_cls = None
                if "종이팩" in name or "우유팩" in name:
                    target_cls = "종이팩"
                elif "종이" in name:
                    target_cls = "종이"
                elif "캔" in name:
                    target_cls = "캔"
                elif "페트병" in name or "플라스틱" in name:
                    target_cls = "플라스틱 & 페트병"
                elif "병" in name or "유리" in name:
                    target_cls = "유리병"
                elif "없음" in name or "대기" in name:
                    if include_none:
                        target_cls = "없음"

                if target_cls:
                    img_files = list(sub_dir.glob("*.png")) + list(sub_dir.glob("*.jpg")) + list(sub_dir.glob("*.jpeg"))
                    for f in img_files:
                        add_image(target_cls, f)

    # 2. captures/ 디렉토리 재귀적 전수 스캔 (루트 및 날짜별 서브폴더 모두 포함)
    if CAPTURES_DIR.exists():
        for cap_file in CAPTURES_DIR.glob("**/*.*"):
            if cap_file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                stem = cap_file.name
                matched_cls = None
                if "종이팩" in stem:
                    matched_cls = "종이팩"
                elif "종이" in stem:
                    matched_cls = "종이"
                elif "캔" in stem:
                    matched_cls = "캔"
                elif "플라스틱" in stem or "페트병" in stem:
                    matched_cls = "플라스틱 & 페트병"
                elif "유리" in stem or "병" in stem:
                    matched_cls = "유리병"
                elif "없음" in stem:
                    if include_none:
                        matched_cls = "없음"

                if matched_cls:
                    add_image(matched_cls, cap_file)

    return class_dataset

def build_and_train_model(class_dataset: dict, target_dir: Path, model_name: str, epochs_phase1: int = 15, epochs_phase2: int = 10):
    print("\n" + "=" * 75)
    print(f"  🧠 [{model_name} 정밀 재학습 엔진 가동] ({len(class_dataset)}개 범주 수집 완료)")
    print("=" * 75)

    sorted_classes = sorted(list(class_dataset.keys()))
    print(f"  📌 학습 대상 범주: {sorted_classes}")

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
                    arr = (arr / 127.5) - 1.0  # Teachable Machine 전처리 규격 [-1, 1]
                    images.append(arr)
                    y_labels.append(class_idx)
                    loaded_count += 1
            except Exception:
                pass
        print(f"   - '{class_name}': {loaded_count}개 고화질 이미지 성공적 파티셔닝!")

    if len(images) == 0:
        print(f"  ⚠️ [{model_name}] 학습할 이미지가 충분하지 않습니다.")
        return

    X = np.array(images, dtype=np.float32)
    y = np.array(y_labels, dtype=np.int32)
    y_cat = keras.utils.to_categorical(y, num_classes=len(sorted_classes))

    print(f"\n  📊 총 {len(X)}개 텐서 파티셔닝 완료 (Dataset Shape: {X.shape})")

    # 강력한 데이터 증강 (Data Augmentation) - 종이/캔 형태 및 조명 차이 극복
    data_augmentation = keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.2),
        layers.RandomZoom(0.2),
        layers.RandomTranslation(0.15, 0.15),
        layers.RandomContrast(0.15),
    ])

    base_model = keras.applications.MobileNetV2(
        input_shape=(img_size, img_size, 3),
        include_top=False,
        weights='imagenet'
    )
    base_model.trainable = False

    inputs = layers.Input(shape=(img_size, img_size, 3))
    x = data_augmentation(inputs)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(len(sorted_classes), activation='softmax')(x)
    model = keras.Model(inputs, outputs)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    print(f"\n  🚀 [Phase 1] 백본 동결 파인튜닝 (Epochs {epochs_phase1}회)...")
    model.fit(X, y_cat, epochs=epochs_phase1, batch_size=8, verbose=1, shuffle=True)

    print(f"\n  🚀 [Phase 2] 상위 35개 레이어 언동결 미세 파인튜닝 (Epochs {epochs_phase2}회)...")
    base_model.trainable = True
    for layer in base_model.layers[:-35]:
        layer.trainable = False

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    model.fit(X, y_cat, epochs=epochs_phase2, batch_size=8, verbose=1, shuffle=True)

    target_dir.mkdir(parents=True, exist_ok=True)
    h5_path = target_dir / "keras_model.h5"
    txt_path = target_dir / "labels.txt"

    model.save(str(h5_path))

    with open(str(txt_path), "w", encoding="utf-8") as f:
        for idx, name in enumerate(sorted_classes):
            f.write(f"{idx} {name}\n")

    print("\n" + "=" * 75)
    print(f"  🎉 [{model_name} 재학습 성공 완료!] 모델 파일: {h5_path}")
    print(f"  📋 최신 레이블: {sorted_classes}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    # 모델 1 재학습 (4종 쓰레기 카테고리)
    ds1 = collect_dataset(include_none=False)
    build_and_train_model(ds1, MODEL1_DIR, "모델1")

    # 모델 2 재학습 (6종 통합 카테고리: 없음/유리병/종이/종이팩/캔/플라스틱)
    ds2 = collect_dataset(include_none=True)
    build_and_train_model(ds2, MODEL2_DIR, "모델2")
