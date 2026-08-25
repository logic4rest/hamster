"""
햄스터 로봇 AI 모델 로컬 데이터셋 추가 학습 & 파이인튜닝 도구 (v1.0)
======================================================================
실행 방법:
    python tools/train_local_model.py
    또는
    uv run python tools/train_local_model.py
"""

import os
import sys
import time
from pathlib import Path

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "keras_model.h5"
LABELS_PATH = MODELS_DIR / "labels.txt"

def print_training_guide():
    print("\n" + "=" * 70)
    print("  🧠 햄스터 로봇 AI 모델 추가 학습 가이드 (Teachable Machine & Local)")
    print("=" * 70)
    print("  [방법 1: 구글 티처블 머신으로 1분 만에 추가 학습하기 (권장)]")
    print("   1. 웹 브라우저에서 https://teachablemachine.withgoogle.com 에 접속합니다.")
    print("   2. [이미지 프로젝트] ➔ [표준 이미지 모델]을 클릭합니다.")
    print("   3. 원하는 클래스(예: 캔, 비닐, 플라스틱, 종이팩, 종이 등)를 추가하고 웹캠이나 이미지를 업로드합니다.")
    print("   4. [모델 학습시키기 (Train Model)] 버튼을 누릅니다.")
    print("   5. 학습 완료 후 [모델 내보내기 (Export Model)] ➔ [Keras] 탭 ➔ [모델 다운로드]를 클릭합니다.")
    print("   6. 다운로드된 'keras_model.h5' 와 'labels.txt' 파일 2개를")
    print("      'c:\\Users\\User\\Desktop\\hamster\\models\\' 폴더에 덮어씌우면 끝!\n")

    print("  [방법 2: 'data/' 폴더의 데이터로 자동 학습하기]")
    print(f"   현재 'data/' 폴더 위치: {DATA_DIR}")
    
    if DATA_DIR.exists():
        subdirs = [d.name for d in DATA_DIR.iterdir() if d.is_dir()]
        print(f"   수집된 이미지 범주 ({len(subdirs)}개): {', '.join(subdirs)}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    print_training_guide()
