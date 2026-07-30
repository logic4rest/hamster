"""
YOLO Bounding Box 라벨링 & 데이터셋 변환 스크립트
=================================================
data/ 폴더 내의 각 범주별 이미지를 감지하고,
YOLO 포맷의 Bounding Box 라벨 파일(.txt)과 data.yaml을 자동 생성합니다.

사용 방법:
    python tools/generate_yolo_dataset.py
"""

import os
from pathlib import Path
from PIL import Image

# ── 설정 ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR     = PROJECT_ROOT / "data"
OUTPUT_DIR   = PROJECT_ROOT / "yolo_dataset"

# YOLO 클래스 정의
CLASSES = [
    "무색 페트병",
    "병",
    "없음",
    "종이",
    "종이팩(우유팩)",
    "캔",
    "플라스틱",
]

CLASS_TO_ID = {name: idx for idx, name in enumerate(CLASSES)}


def create_yolo_bbox_annotation(img_path: Path, label_path: Path, class_id: int):
    """
    중앙 영역 (80% 가득 찬 객체) 기준으로 YOLO normalized BBox (.txt) 라벨 생성
    YOLO 형식: <class_id> <x_center> <y_center> <width> <height>
    """
    # 기본 사각형: x_center=0.5, y_center=0.5, width=0.8, height=0.8
    x_center = 0.5
    y_center = 0.5
    width    = 0.8
    height   = 0.8

    label_content = f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"

    with open(label_path, "w", encoding="utf-8") as f:
        f.write(label_content)


def generate_dataset():
    print(f"[INFO] YOLO 데이터셋 변환 시작... ({DATA_DIR} -> {OUTPUT_DIR})")
    
    images_out = OUTPUT_DIR / "images"
    labels_out = OUTPUT_DIR / "labels"

    images_out.mkdir(parents=True, exist_ok=True)
    labels_out.mkdir(parents=True, exist_ok=True)

    total_converted = 0

    for category in CLASSES:
        cat_dir = DATA_DIR / category
        if not cat_dir.exists():
            print(f"[WARN] 폴더 없음: {cat_dir}")
            continue

        class_id = CLASS_TO_ID[category]
        img_files = [f for f in cat_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')]

        print(f"  → 범주 [{category}] (ID: {class_id}): {len(img_files)}개 이미지 처리 중...")

        for img_file in img_files:
            # 이미지 파일 복사 또는 읽기 확인
            try:
                with Image.open(img_file) as img:
                    img.verify()
            except Exception as e:
                print(f"    [오류] 손상된 이미지 스킵: {img_file.name} ({e})")
                continue

            # 파일명 정규화
            safe_name = f"{class_id}_{img_file.stem}"
            dest_img  = images_out / f"{safe_name}{img_file.suffix}"
            dest_lbl  = labels_out / f"{safe_name}.txt"

            # 이미지 복사
            dest_img.write_bytes(img_file.read_bytes())

            # YOLO BBox 라벨 생성
            create_yolo_bbox_annotation(img_file, dest_lbl, class_id)
            total_converted += 1

    # data.yaml 생성
    yaml_content = f"""path: {OUTPUT_DIR.resolve()}
train: images
val: images

nc: {len(CLASSES)}
names: {CLASSES}
"""
    yaml_path = OUTPUT_DIR / "data.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")

    print("\n" + "=" * 50)
    print(f"✔ YOLO 데이터셋 생성이 완료되었습니다!")
    print(f"  - 총 변환 이미지 수: {total_converted}개")
    print(f"  - 데이터셋 경로: {OUTPUT_DIR}")
    print(f"  - 설정 파일: {yaml_path}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    generate_dataset()
