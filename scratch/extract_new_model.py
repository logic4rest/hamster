import zipfile
from pathlib import Path

zip_path = Path(r"C:\Users\User\Downloads\converted_keras.zip")
models_dir = Path(r"C:\Users\User\Desktop\hamster\models")

if zip_path.exists():
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(models_dir)
    print(f"[OK] {zip_path} 압축 해제 완료! 대상: {models_dir}")
else:
    print(f"[ERROR] {zip_path} 파일이 존재하지 않습니다.")
