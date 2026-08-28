import os
from pathlib import Path

data_dir = Path("c:/Users/User/Desktop/hamster/data")
for sub in data_dir.iterdir():
    if sub.is_dir():
        imgs = list(sub.glob("*.*"))
        print(f"클래스: {sub.name} -> {len(imgs)}개 이미지")
