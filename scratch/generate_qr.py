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
github_url = "https://logic4rest.github.io/hamster/"

# 1. QR 코드 생성 (모든 기능 1초 원클릭 접속)
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=2,
)
qr.add_data(web_url)
qr.make(fit=True)

qr_img = qr.make_image(fill_color="#00f2fe", back_color="#0b0f19").convert('RGB')
qr_w, qr_h = qr_img.size

# 2. 카드 배너 캔버스 생성
banner_w = qr_w + 80
banner_h = qr_h + 160
banner = Image.new('RGB', (banner_w, banner_h), color='#0b0f19')
draw = ImageDraw.Draw(banner)

# 테두리 및 둥근 카드 느낌
draw.rectangle([5, 5, banner_w - 5, banner_h - 5], outline='#00f2fe', width=3)

# QR 코드 붙이기
banner.paste(qr_img, (40, 90))

# 텍스트 렌더링
try:
    font_title = ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 20)
    font_sub = ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 14)
except Exception:
    font_title = ImageFont.load_default()
    font_sub = ImageFont.load_default()

draw.text((banner_w // 2, 35), "🐹 AI 햄스터 로봇 관제센터", font=font_title, fill="#00f2fe", anchor="mm")
draw.text((banner_w // 2, 65), "스마트폰 QR 원클릭 통합 접속", font=font_sub, fill="#94a3b8", anchor="mm")

draw.text((banner_w // 2, banner_h - 45), f"URL: {web_url}", font=font_sub, fill="#ffffff", anchor="mm")
draw.text((banner_w // 2, banner_h - 20), "2D 시뮬레이터 | 터치조종 | AI 분리배출 | EXE 다운로드", font=font_sub, fill="#34d399", anchor="mm")

# 저장
output_path1 = "c:/Users/User/Desktop/hamster/web_hamster_qr.png"
output_path2 = "c:/Users/User/Desktop/햄스터_원클릭_통합QR.png"

banner.save(output_path1)
banner.save(output_path2)

print(f"[SUCCESS] QR 코드 배너 생성 완료: {output_path1}, {output_path2}")
