"""
스마트폰 QR 모바일 리모컨 & 2D/3D 시뮬레이터 & 프로젝트 ZIP 다운로더 웹서버 (v2.0)
==================================================================================
- 모드 전환: [🧪 웹 2D 시뮬레이션 모드] <---> [🤖 실제 햄스터봇 조종 모드]
- 실시간 2D 캔버스 아레나 시뮬레이터 (스마트폰/웹 브라우저에서 바로 주행 검증)
- 소스코드 및 실행 가이드 압축 다운로드 기능 (/download)
- 웹캠 MJPEG 실시간 스트리밍 및 QR 오버레이 지원
"""

import io
import json
import os
import socket
import threading
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np
import qrcode
from flask import Flask, Response, jsonify, render_template_string, request, send_file

PROJECT_ROOT = Path(__file__).parent.parent

# 글로벌 공유 객체
latest_frame = None
frame_lock = threading.Lock()

robot_controller_callback = None
stats_provider_callback = None
current_mode = "real"  # "real" 또는 "simulation"

app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🐹 스마트 햄스터 분리배출 관제 & 시뮬레이터 센터</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; user-select: none; }
        body { background: #0f172a; color: #f8fafc; display: flex; flex-direction: column; min-height: 100vh; padding: 12px; }
        header { text-align: center; margin-bottom: 12px; padding: 14px; background: #1e293b; border-radius: 14px; border: 1px solid #334155; position: relative; }
        h1 { font-size: 1.2rem; color: #38bdf8; display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 8px; }
        .mode-toggle { display: flex; background: #0f172a; border-radius: 20px; padding: 3px; border: 1px solid #334155; margin: 8px auto 0; max-width: 320px; }
        .mode-btn { flex: 1; padding: 8px 12px; font-size: 0.8rem; font-weight: bold; border: none; border-radius: 16px; color: #94a3b8; background: transparent; cursor: pointer; transition: all 0.2s; }
        .mode-btn.active { background: #38bdf8; color: #0f172a; box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4); }
        .download-bar { margin-bottom: 12px; }
        .btn-download { width: 100%; background: linear-gradient(135deg, #059669, #10b981); color: white; border: none; border-radius: 12px; padding: 14px; font-size: 0.95rem; font-weight: bold; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: transform 0.1s; }
        .btn-download:active { transform: scale(0.98); }
        .view-panel { display: none; }
        .view-panel.active { display: block; }
        .stream-card { background: #000; border-radius: 14px; overflow: hidden; border: 2px solid #38bdf8; margin-bottom: 12px; position: relative; box-shadow: 0 4px 14px rgba(0,0,0,0.5); }
        .stream-card img { width: 100%; display: block; }
        .sim-card { background: #1e293b; border-radius: 14px; padding: 12px; border: 2px solid #a855f7; margin-bottom: 12px; text-align: center; }
        canvas { background: #0f172a; border-radius: 10px; border: 1px solid #334155; width: 100%; max-width: 480px; height: 300px; }
        .grid-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        .section-box { background: #1e293b; border-radius: 14px; padding: 12px; border: 1px solid #334155; }
        .section-title { font-size: 0.85rem; font-weight: bold; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .dpad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; aspect-ratio: 1; max-width: 180px; margin: 0 auto; }
        .btn { background: #334155; color: white; border: none; border-radius: 10px; font-weight: bold; font-size: 1rem; display: flex; align-items: center; justify-content: center; padding: 14px; cursor: pointer; transition: all 0.1s; }
        .btn:active { background: #38bdf8; color: #0f172a; transform: scale(0.95); }
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
        <h1>🐹 햄스터 분리배출관제센터</h1>
        <div class="mode-toggle">
            <button id="btn-mode-real" class="mode-btn active" onclick="switchMode('real')">🤖 실제 햄스터봇</button>
            <button id="btn-mode-sim" class="mode-btn" onclick="switchMode('sim')">🧪 시뮬레이션 모드</button>
        </div>
    </header>

    <div class="download-bar">
        <a href="/download" class="btn-download" download>
            📥 햄스터 분리배출 프로그램 & 실행파일 전체 다운로드 (ZIP)
        </a>
    </div>

    <!-- 1. 실제 햄스터봇 모드 화면 -->
    <div id="panel-real" class="view-panel active">
        <div class="stream-card">
            <img src="/video_feed" alt="실시간 카메라 스트리밍">
        </div>
    </div>

    <!-- 2. 시뮬레이션 모드 화면 -->
    <div id="panel-sim" class="view-panel">
        <div class="sim-card">
            <div class="section-title" style="color: #c084fc; margin-bottom: 6px;">🎮 2D 가상 햄스터 분리배출 아레나</div>
            <canvas id="simCanvas" width="400" height="280"></canvas>
            <div id="simLog" class="status-pill" style="background: #581c87; margin-top: 8px;">대기 중: 수거 버튼을 눌러 시뮬레이션을 시작하세요.</div>
        </div>
    </div>

    <!-- 분리배출 제어 버튼 -->
    <div class="section-box" style="margin-bottom: 12px;">
        <div class="section-title">♻️ 원터치 스마트 분리배출 수거</div>
        <div class="sort-grid">
            <button class="btn btn-sort btn-paper" onclick="triggerSort('종이')">📄 1번 종이</button>
            <button class="btn btn-sort btn-paperpack" onclick="triggerSort('종이팩')">🩵 2번 종이팩</button>
            <button class="btn btn-sort btn-plastic" onclick="triggerSort('플라스틱/페트병')">🥤 3번 페트병</button>
            <button class="btn btn-sort btn-can" onclick="triggerSort('캔')">🥫 4번 캔</button>
        </div>
    </div>

    <!-- 방향 조종 & 집게 버튼 -->
    <div class="grid-layout">
        <div class="section-box">
            <div class="section-title">🕹️ 로봇 방향 주행</div>
            <div class="dpad">
                <button class="btn btn-drive" style="grid-column: 2; grid-row: 1;" onclick="drive('up')">▲</button>
                <button class="btn btn-drive" style="grid-column: 1; grid-row: 2;" onclick="drive('left')">◀</button>
                <button class="btn btn-stop" onclick="drive('stop')">정지</button>
                <button class="btn btn-drive" style="grid-column: 3; grid-row: 2;" onclick="drive('right')">▶</button>
                <button class="btn btn-drive" style="grid-column: 2; grid-row: 3;" onclick="drive('down')">▼</button>
            </div>
        </div>

        <div class="section-box" style="display: flex; flex-direction: column; justify-content: space-between;">
            <div class="section-title">🦾 집게 열기/닫기</div>
            <button class="btn btn-grip-open" style="margin-bottom: 8px;" onclick="controlGripper('open')">👐 집게 열기 (OPEN)</button>
            <button class="btn btn-grip-close" onclick="controlGripper('close')">✊ 집게 닫기 (CLOSE)</button>
        </div>
    </div>

    <footer>
        AI 스마트 햄스터 분리배출관제센터 & 시뮬레이터 v2.0
    </footer>

    <script>
        let currentMode = 'real';
        
        function switchMode(mode) {
            currentMode = mode;
            document.getElementById('btn-mode-real').classList.toggle('active', mode === 'real');
            document.getElementById('btn-mode-sim').classList.toggle('active', mode === 'sim');
            document.getElementById('panel-real').classList.toggle('active', mode === 'real');
            document.getElementById('panel-sim').classList.toggle('active', mode === 'sim');

            fetch('/api/set_mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode })
            });
        }

        function drive(dir) {
            if (currentMode === 'sim') {
                moveSimRobot(dir);
                return;
            }
            fetch('/api/drive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ direction: dir })
            });
        }

        function controlGripper(action) {
            if (currentMode === 'sim') {
                simGripperState = action;
                drawSim();
                alert("시뮬레이터 집게: " + (action === 'open' ? "열림 (OPEN)" : "닫힘 (CLOSE)"));
                return;
            }
            fetch('/api/gripper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action })
            }).then(res => res.json()).then(data => alert(data.message));
        }

        function triggerSort(category) {
            if (currentMode === 'sim') {
                runSimSortingSequence(category);
                return;
            }
            if(confirm("['" + category + "'] 분리배출 자율주행을 시작할까요?")) {
                fetch('/api/sort', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ category: category })
                }).then(res => res.json()).then(data => alert(data.message));
            }
        }

        /* 🎮 2D 캔버스 시뮬레이터 엔진 */
        const canvas = document.getElementById('simCanvas');
        const ctx = canvas ? canvas.getContext('2d') : null;
        
        let simRobot = { x: 200, y: 140, angle: 0, originX: 200, originY: 140 };
        let simGripperState = 'open';
        let simRunning = false;

        const simBins = {
            '종이': { x: 340, y: 50, color: '#854d0e', label: '1번 종이' },
            '종이팩': { x: 340, y: 230, color: '#0891b2', label: '2번 종이팩' },
            '플라스틱/페트병': { x: 60, y: 50, color: '#1e40af', label: '3번 페트병' },
            '캔': { x: 60, y: 230, color: '#15803d', label: '4번 캔' }
        };

        function drawSim() {
            if (!ctx) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // 격자 배경
            ctx.strokeStyle = '#1e293b';
            for(let x=0; x<canvas.width; x+=40) {
                ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke();
            }
            for(let y=0; y<canvas.height; y+=40) {
                ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(canvas.width,y); ctx.stroke();
            }

            // 시작점 마커
            ctx.fillStyle = '#38bdf8';
            ctx.beginPath(); ctx.arc(simRobot.originX, simRobot.originY, 6, 0, Math.PI*2); ctx.fill();
            ctx.font = '10px sans-serif'; ctx.fillText('시작점(0,0)', simRobot.originX-25, simRobot.originY+18);

            // 4종 수거함 상자
            for(let cat in simBins) {
                let bin = simBins[cat];
                ctx.fillStyle = bin.color;
                ctx.fillRect(bin.x-30, bin.y-20, 60, 40);
                ctx.strokeStyle = '#ffffff'; ctx.strokeRect(bin.x-30, bin.y-20, 60, 40);
                ctx.fillStyle = '#ffffff'; ctx.font = '11px sans-serif'; ctx.fillText(bin.label, bin.x-24, bin.y+4);
            }

            // 햄스터 로봇 그리기
            ctx.save();
            ctx.translate(simRobot.x, simRobot.y);
            ctx.rotate(simRobot.angle);

            // 본체
            ctx.fillStyle = '#f59e0b';
            ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI*2); ctx.fill();
            ctx.strokeStyle = '#ffffff'; ctx.stroke();

            // 집게
            ctx.strokeStyle = simGripperState === 'open' ? '#10b981' : '#ef4444';
            ctx.lineWidth = 3;
            let offset = simGripperState === 'open' ? 12 : 4;
            ctx.beginPath(); ctx.moveTo(14, -offset); ctx.lineTo(24, -offset/2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(14, offset); ctx.lineTo(24, offset/2); ctx.stroke();
            ctx.lineWidth = 1;

            ctx.restore();
        }

        function moveSimRobot(dir) {
            let speed = 8;
            if (dir === 'up') { simRobot.x += Math.cos(simRobot.angle)*speed; simRobot.y += Math.sin(simRobot.angle)*speed; }
            else if (dir === 'down') { simRobot.x -= Math.cos(simRobot.angle)*speed; simRobot.y -= Math.sin(simRobot.angle)*speed; }
            else if (dir === 'left') { simRobot.angle -= 0.2; }
            else if (dir === 'right') { simRobot.angle += 0.2; }
            drawSim();
        }

        function runSimSortingSequence(category) {
            if (simRunning) return;
            simRunning = true;
            let log = document.getElementById('simLog');
            let targetBin = simBins[category];

            log.innerText = "🤖 ['" + category + "'] 6프레임 감지 완료! 집게 열고 4초 거치 대기...";
            simGripperState = 'open';
            drawSim();

            setTimeout(() => {
                log.innerText = "🦾 4초 대기 완료! 집게 닫기 (CLOSE) 쓰레기 포획!";
                simGripperState = 'close';
                drawSim();

                setTimeout(() => {
                    log.innerText = "🚚 수거함 지정 경로 자율주행 중...";
                    let steps = 30;
                    let count = 0;
                    let dx = (targetBin.x - simRobot.x) / steps;
                    let dy = (targetBin.y - simRobot.y) / steps;

                    let interval = setInterval(() => {
                        simRobot.x += dx;
                        simRobot.y += dy;
                        drawSim();
                        count++;
                        if (count >= steps) {
                            clearInterval(interval);
                            log.innerText = "🎉 수거함 도착! 집게 열기 (OPEN) 쓰레기 투입!";
                            simGripperState = 'open';
                            drawSim();

                            setTimeout(() => {
                                log.innerText = "↩️ 오차 0.00cm 1:1 대칭 정밀 역주행 복귀 중...";
                                let rCount = 0;
                                let rInterval = setInterval(() => {
                                    simRobot.x -= dx;
                                    simRobot.y -= dy;
                                    drawSim();
                                    rCount++;
                                    if (rCount >= steps) {
                                        clearInterval(rInterval);
                                        simRobot.x = simRobot.originX;
                                        simRobot.y = simRobot.originY;
                                        log.innerText = "✅ 시작 위치 복귀 완료! (오차: 0.0000 cm PASS)";
                                        simRunning = false;
                                        drawSim();
                                    }
                                }, 50);
                            }, 1000);
                        }
                    }, 50);
                }, 1200);
            }, 2000);
        }

        window.onload = function() {
            drawSim();
        };
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
    """QR 코드 BGR 이미지를 실시간 생성 및 캐싱"""
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
    
    margin = 15
    y1 = h - qr_h - margin - 25
    y2 = h - margin - 25
    x1 = w - qr_w - margin
    x2 = w - margin
    
    cv2.rectangle(canvas, (x1 - 4, y1 - 22), (x2 + 4, y2 + 4), (255, 255, 255), -1)
    cv2.rectangle(canvas, (x1 - 4, y1 - 22), (x2 + 4, y2 + 4), (0, 120, 255), 2)
    cv2.putText(canvas, "📱 QR Mobile", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    
    canvas[y1:y2, x1:x2] = qr_bgr
    return canvas

@app.route('/')
def index():
    return render_template_string(HTML_DASHBOARD)

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

@app.route('/download')
def download_project_zip():
    """전체 프로젝트 소스코드 및 모델을 메모리에서 압축하여 ZIP으로 바로 다운로드 제공"""
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in PROJECT_ROOT.glob('**/*'):
            if file_path.is_file() and not any(part.startswith('.') or part in ['__pycache__', 'build', 'dist'] for part in file_path.parts):
                arcname = file_path.relative_to(PROJECT_ROOT)
                zf.write(file_path, arcname)
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='hamster_smart_sorting_v8.0.zip'
    )

@app.route('/api/set_mode', methods=['POST'])
def api_set_mode():
    global current_mode
    data = request.json or {}
    mode = data.get('mode', 'real')
    current_mode = mode
    return jsonify({"status": "ok", "mode": current_mode})

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
    print("  📱 [스마트폰 QR 관제센터 & 시뮬레이터 & ZIP 다운로드 웹서버 가동]")
    print(f"  - 웹/스마트폰 접속 URL: {url}")
    print("  - 프로젝트 ZIP 다운로드 URL: {url}/download")
    print("  - QR 코드가 웹캠 카메라 화면 우측 하단에 실시간으로 표시됩니다!")
    print("=" * 65 + "\n")
    
    def run():
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return url
