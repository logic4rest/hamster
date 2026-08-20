import os
import shutil
import sys
from pathlib import Path

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

src_data_dir = Path(r"C:\Users\User\Desktop\hamster\data")
dst_desktop_dir = Path(r"C:\Users\User\Desktop\Data")

if dst_desktop_dir.exists():
    shutil.rmtree(dst_desktop_dir)

shutil.copytree(src_data_dir, dst_desktop_dir)

file_count = 0
for root, dirs, files in os.walk(dst_desktop_dir):
    file_count += len(files)

print(f"[OK] 바탕화면 C:\\Users\\User\\Desktop\\Data 폴더에 총 {file_count}개의 이미지 데이터 세트가 모두 저장되었습니다!")
