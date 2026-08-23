import os
import socket
import qrcode
from PIL import Image, ImageDraw, ImageFont

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

ip = get_local_ip()
web_url = f"http://{ip}:5000"

# 1. 고해상도 QR 코드 생성
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=12,
    border=2,
)
qr.add_data(web_url)
qr.make(fit=True)

qr_img = qr.make_image(fill_color="#00f2fe", back_color="#0b0f19").convert('RGB')
qr_w, qr_h = qr_img.size

# 2. 카드 배너 캔버스 생성
banner_w = qr_w + 100
banner_h = qr_h + 180
banner = Image.new('RGB', (banner_w, banner_h), color='#0b0f19')
draw = ImageDraw.Draw(banner)

# 테두리
draw.rectangle([6, 6, banner_w - 6, banner_h - 6], outline='#00f2fe', width=4)

# QR 코드 부착
banner.paste(qr_img, (50, 100))

# 폰트 렌더링
try:
    font_title = ImageFont.truetype("c:/Windows/Fonts/malgunbd.ttf", 22)
    font_sub = ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 15)
except Exception:
    font_title = ImageFont.load_default()
    font_sub = ImageFont.load_default()

draw.text((banner_w // 2, 40), "🐹 AI 햄스터 로봇 관제센터", font=font_title, fill="#00f2fe", anchor="mm")
draw.text((banner_w // 2, 72), "스마트폰 카메라로 QR을 스캔하세요", font=font_sub, fill="#94a3b8", anchor="mm")

draw.text((banner_w // 2, banner_h - 50), f"접속 주소: {web_url}", font=font_sub, fill="#ffffff", anchor="mm")
draw.text((banner_w // 2, banner_h - 24), "2D 시뮬레이터 | 터치 조종 | AI 분리배출 | EXE 다운로드", font=font_sub, fill="#34d399", anchor="mm")

# 파일 저장
path1 = "c:/Users/User/Desktop/hamster/web_hamster_qr.png"
path2 = "c:/Users/User/Desktop/햄스터_스마트폰_QR코드.png"

banner.save(path1)
banner.save(path2)

print(f"[SUCCESS] QR 코드 이미지 생성 완결: {path1}, {path2}")
