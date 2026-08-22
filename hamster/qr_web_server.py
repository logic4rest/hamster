"""
스마트폰 QR 모바일 리모컨 웹서버 및 QR 코드 렌더러 (v1.0)
======================================================================
- 스마트폰 카메라인식 QR 코드를 카메라 화면에 실시간 오버레이
- 스마트폰 웹 브라우저(HTML5)를 통한 스마트 햄스터 로봇 실시간 조종 & 수거 명령
- 웹캠 MJPEG 실시간 스트리밍 제공
"""

import io
import socket
import threading
import time
from pathlib import Path
import cv2
import numpy as np
import qrcode
from flask import Flask, Response, jsonify, render_template_string, request

# 글로벌 공유 객체 (카메라 프레임 및 제어 콜백)
latest_frame = None
frame_lock = threading.Lock()

robot_controller_callback = None
stats_provider_callback = None

app = Flask(__name__)

HTML_MOBILE_UI = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🐹 햄스터 로봇 스마트 모바일 리모컨</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; user-select: none; }
        body { background: #0f172a; color: #f8fafc; display: flex; flex-direction: column; min-height: 100vh; padding: 12px; }
        header { text-align: center; margin-bottom: 12px; padding: 10px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; }
        h1 { font-size: 1.1rem; color: #38bdf8; display: flex; align-items: center; justify-content: center; gap: 8px; }
        .stream-card { background: #000; border-radius: 12px; overflow: hidden; border: 2px solid #38bdf8; margin-bottom: 12px; position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
        .stream-card img { width: 100%; display: block; }
        .grid-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        .section-box { background: #1e293b; border-radius: 12px; padding: 12px; border: 1px solid #334155; }
        .section-title { font-size: 0.85rem; font-weight: bold; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .dpad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; aspect-ratio: 1; max-width: 200px; margin: 0 auto; }
        .btn { background: #334155; color: white; border: none; border-radius: 10px; font-weight: bold; font-size: 1rem; display: flex; align-items: center; justify-content: center; padding: 14px; cursor: pointer; transition: all 0.1s; active { transform: scale(0.95); } }
        .btn:active { background: #38bdf8; color: #0f172a; }
        .btn-drive { font-size: 1.3rem; background: #3b82f6; }
        .btn-stop { background: #ef4444; color: white; grid-column: 2; grid-row: 2; font-size: 0.9rem; }
        .btn-grip-open { background: #10b981; }
        .btn-grip-close { background: #f59e0b; }
        .sort-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .btn-sort { font-size: 0.9rem; padding: 12px 6px; flex-direction: column; gap: 4px; border: 1px solid rgba(255,255,255,0.1); }
        .btn-paper { background: #854d0e; }
        .btn-paperpack { background: #0891b2; }
        .btn-plastic { background: #1e40af; }
        .btn-can { background: #15803d; }
        .status-pill { font-size: 0.75rem; background: #0284c7; padding: 4px 8px; border-radius: 20px; text-align: center; margin-top: 6px; }
        footer { font-size: 0.7rem; text-align: center; color: #64748b; margin-top: auto; padding-top: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>🐹 햄스터 스마트 로봇 스마트폰 리모컨</h1>
        <div id="connection-status" class="status-pill">📱 스마트폰 웹 연결됨</div>
    </header>

    <div class="stream-card">
        <img src="/video_feed" alt="실시간 햄스터 카메라">
    </div>

    <div class="section-box" style="margin-bottom: 12px;">
        <div class="section-title">♻️ 원터치 스마트 분리배출 자율 수거</div>
        <div class="sort-grid">
            <button class="btn btn-sort btn-paper" onclick="triggerSort('종이')">📄 1번 종이</button>
            <button class="btn btn-sort btn-paperpack" onclick="triggerSort('종이팩')">🩵 2번 종이팩</button>
            <button class="btn btn-sort btn-plastic" onclick="triggerSort('플라스틱/페트병')">🥤 3번 페트병</button>
            <button class="btn btn-sort btn-can" onclick="triggerSort('캔')">🥫 4번 캔</button>
        </div>
    </div>

    <div class="grid-layout">
        <div class="section-box">
            <div class="section-title">🕹️ 로봇 방향 주행</div>
            <div class="dpad">
                <button class="btn btn-drive" style="grid-column: 2; grid-row: 1;" ontouchstart="drive('up')" ontouchend="drive('stop')" mousedown="drive('up')" mouseup="drive('stop')">▲</button>
                <button class="btn btn-drive" style="grid-column: 1; grid-row: 2;" ontouchstart="drive('left')" ontouchend="drive('stop')" mousedown="drive('left')" mouseup="drive('stop')">◀</button>
                <button class="btn btn-stop" onclick="drive('stop')">정지</button>
                <button class="btn btn-drive" style="grid-column: 3; grid-row: 2;" ontouchstart="drive('right')" ontouchend="drive('stop')" mousedown="drive('right')" mouseup="drive('stop')">▶</button>
                <button class="btn btn-drive" style="grid-column: 2; grid-row: 3;" ontouchstart="drive('down')" ontouchend="drive('stop')" mousedown="drive('down')" mouseup="drive('stop')">▼</button>
            </div>
        </div>

        <div class="section-box" style="display: flex; flex-direction: column; justify-content: space-between;">
            <div class="section-title">🦾 집게 오무리기/펴기</div>
            <button class="btn btn-grip-open" style="margin-bottom: 8px;" onclick="controlGripper('open')">👐 집게 펴기 (OPEN)</button>
            <button class="btn btn-grip-close" onclick="controlGripper('close')">✊ 집게 오무리기 (CLOSE)</button>
        </div>
    </div>

    <footer>
        AI 햄스터봇 스마트 분리배출 자율주행 스마트폰 웹 조종기 v1.0
    </footer>

    <script>
        function drive(dir) {
            fetch('/api/drive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ direction: dir })
            }).catch(err => console.error(err));
        }

        function controlGripper(action) {
            fetch('/api/gripper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action })
            }).then(res => res.json()).then(data => {
                alert(data.message);
            }).catch(err => console.error(err));
        }

        function triggerSort(category) {
            if(confirm("['" + category + "'] 분리배출 자율주행을 시작할까요?")) {
                fetch('/api/sort', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category: category })
                }).then(res => res.json()).then(data => {
                    alert(data.message);
                }).catch(err => console.error(err));
            }
        }
    </script>
</body>
</html>
"""

def get_local_ip() -> str:
    """PC의 로컬 네트워크 IP 주소 자동 검색"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

_cached_qr_image = None
_qr_url = None

def get_qr_overlay_bgr(url: str, size: int = 140) -> np.ndarray:
    """QR 코드 BGR 이미지를 실시간 생상 및 캐싱"""
    global _cached_qr_image, _qr_url
    if _cached_qr_image is not None and _qr_url == url:
        return _cached_qr_image

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img_pil = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    img_pil = img_pil.resize((size, size))
    
    img_bgr = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    _cached_qr_image = img_bgr
    _qr_url = url
    return _cached_qr_image

def update_web_frame(frame: np.ndarray):
    """OpenCV 웹캠 프레임을 웹 스트리밍용으로 업데이트"""
    global latest_frame
    if frame is None:
        return
    with frame_lock:
        latest_frame = frame.copy()

def overlay_qr_code_on_frame(frame: np.ndarray, server_url: str) -> np.ndarray:
    """OpenCV 프레임 우측 하단에 스마트폰 인식용 QR 코드를 실시간 합성"""
    if frame is None:
        return frame
    
    canvas = frame.copy()
    h, w, _ = canvas.shape
    
    qr_bgr = get_qr_overlay_bgr(server_url, size=130)
    qr_h, qr_w, _ = qr_bgr.shape
    
    # 우측 하단에 패딩을 주고 오버레이
    margin = 15
    y1 = h - qr_h - margin - 25
    y2 = h - margin - 25
    x1 = w - qr_w - margin
    x2 = w - margin
    
    # 흰색 배경 프레임 테두리 박스
    cv2.rectangle(canvas, (x1 - 4, y1 - 22), (x2 + 4, y2 + 4), (255, 255, 255), -1)
    cv2.rectangle(canvas, (x1 - 4, y1 - 22), (x2 + 4, y2 + 4), (0, 120, 255), 2)
    
    # 상단 텍스트 "📱 스마트폰 QR 스캔"
    cv2.putText(canvas, "📱 QR Mobile", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    
    # QR 이미지 합성
    canvas[y1:y2, x1:x2] = qr_bgr
    return canvas

@app.route('/')
def index():
    return render_template_string(HTML_MOBILE_UI)

def generate_mjpeg_stream():
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is None:
                time.sleep(0.05)
                continue
            ret, jpeg = cv2.imencode('.jpg', latest_frame)
            if not ret:
                time.sleep(0.05)
                continue
            frame_bytes = jpeg.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/drive', methods=['POST'])
def api_drive():
    data = request.json or {}
    direction = data.get('direction', 'stop')
    if robot_controller_callback:
        robot_controller_callback('drive', direction)
    return jsonify({"status": "ok", "direction": direction})

@app.route('/api/gripper', methods=['POST'])
def api_gripper():
    data = request.json or {}
    action = data.get('action', 'open')
    if robot_controller_callback:
        robot_controller_callback('gripper', action)
    return jsonify({"status": "ok", "message": f"집게 제어: {action}"})

@app.route('/api/sort', methods=['POST'])
def api_sort():
    data = request.json or {}
    category = data.get('category', '종이')
    if robot_controller_callback:
        robot_controller_callback('sort', category)
    return jsonify({"status": "ok", "message": f"'{category}' 분리배출 자율 수거를 시작합니다."})

def start_qr_web_server(port: int = 5000) -> str:
    """웹서버를 백그라운드 데몬 쓰레드로 가동하고 접속 URL 반환"""
    ip = get_local_ip()
    url = f"http://{ip}:{port}"
    
    print("\n" + "=" * 65)
    print("  📱 [스마트폰 QR 모바일 리모컨 웹서버 가동]")
    print(f"  - 스마트폰 카메라 접속 URL: {url}")
    print("  - QR 코드가 웹캠 카메라 화면 우측 하단에 실시간으로 표시됩니다!")
    print("  - 스마트폰 카메라로 QR 코드를 스캔하면 바로 조종 화면이 열립니다.")
    print("=" * 65 + "\n")
    
    def run():
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return url
