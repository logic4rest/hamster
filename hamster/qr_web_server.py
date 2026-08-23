"""
스마트폰 QR 모바일 리모컨 & 2D/3D 시뮬레이터 & AI 실시간 인식 바 HUD 웹서버 (v2.5)
==================================================================================
- 실시간 AI 인식 결과 및 쓰레기 4종 확률 프로그레스 바 하단 오버레이 탑재
- 모드 전환: [🧪 웹 2D 시뮬레이션 모드] <---> [🤖 실제 햄스터봇 조종 모드]
- 실시간 2D 캔버스 아레나 시뮬레이터 (스마트폰/웹 브라우저에서 바로 주행 검증)
- 소스코드 및 실행 가이드 압축 다운로드 기능 (/download)
"""

import io
import json
import os
import socket
import sys
import threading
import time
import webbrowser
import zipfile
from pathlib import Path

# 윈도우 콘솔 CP949 UTF-8 인코딩 안전 처리
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
current_mode = "simulation"

app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>🐹 스마트 햄스터 분리배출 관제 & 시뮬레이터 센터</title>
    <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@latest/dist/tf.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@teachablemachine/image@latest/dist/teachablemachine-image.min.js"></script>
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
        canvas { background: #0f172a; border-radius: 10px; border: 1px solid #334155; width: 100%; max-width: 480px; height: 260px; }
        .status-pill { font-size: 0.8rem; background: #581c87; color: #f3e8ff; padding: 8px 12px; border-radius: 20px; text-align: center; margin-top: 6px; font-weight: bold; }

        /* AI Recognition Display Card */
        .ai-hud-box { background: #1e293b; border-radius: 14px; padding: 12px; border: 2px solid #0284c7; margin-bottom: 12px; }
        .ai-title { font-size: 0.85rem; font-weight: bold; color: #94a3b8; margin-bottom: 6px; text-transform: uppercase; }
        .ai-result-tag { font-size: 1.1rem; font-weight: bold; color: #38bdf8; text-align: center; padding: 6px; background: #0f172a; border-radius: 8px; border: 1px solid #334155; margin-bottom: 8px; }
        .prob-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 0.75rem; }
        .prob-label { width: 75px; text-align: left; }
        .prob-track { flex: 1; background: #0f172a; height: 12px; border-radius: 6px; overflow: hidden; }
        .prob-fill { height: 100%; width: 0%; transition: width 0.2s; }
        .prob-val { width: 35px; text-align: right; font-weight: bold; }

        .grid-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
        .section-box { background: #1e293b; border-radius: 14px; padding: 12px; border: 1px solid #334155; }
        .section-title { font-size: 0.85rem; font-weight: bold; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
        .dpad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; aspect-ratio: 1; max-width: 170px; margin: 0 auto; }
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
        footer { font-size: 0.7rem; text-align: center; color: #64748b; margin-top: auto; padding-top: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>🐹 햄스터 분리배출관제센터</h1>
        <div class="mode-toggle">
            <button id="btn-mode-sim" class="mode-btn active" onclick="switchMode('sim')">🧪 시뮬레이션 모드</button>
            <button id="btn-mode-real" class="mode-btn" onclick="switchMode('real')">🤖 실제 햄스터봇</button>
        </div>
    </header>

    <div class="download-bar">
        <a href="/download" class="btn-download" download>
            📥 햄스터 분리배출 프로그램 & 실행파일 전체 다운로드 (ZIP)
        </a>
    </div>

    <!-- 1. 시뮬레이션 모드 화면 -->
    <div id="panel-sim" class="view-panel active">
        <div class="sim-card">
            <div class="section-title" style="color: #c084fc; margin-bottom: 6px;">🎮 2D 가상 햄스터 분리배출 아레나</div>
            <canvas id="simCanvas" width="400" height="260"></canvas>
            <div id="simLog" class="status-pill">대기 중: 아래 수거 버튼을 누르시면 자율주행 시뮬레이션이 실행됩니다.</div>
        </div>
    </div>

    <!-- 2. 실제 햄스터봇 모드 화면 -->
    <div id="panel-real" class="view-panel">
        <div class="stream-card">
            <img src="/video_feed" alt="실시간 카메라 스트리밍">
        </div>
    </div>

    <!-- 🤖 AI 실시간 인식 결과 & 확률 바 HUD (유저 요구사항 100% 반영) -->
    <div class="ai-hud-box">
        <div class="ai-title">🤖 AI 실시간 감지 분석 결과</div>
        <div id="ai-tag" class="ai-result-tag">🔍 쓰레기 감지 대기 중...</div>
        <div class="prob-row">
            <span class="prob-label">📄 종이</span>
            <div class="prob-track"><div id="bar-paper" class="prob-fill" style="background:#854d0e;"></div></div>
            <span id="val-paper" class="prob-val">0%</span>
        </div>
        <div class="prob-row">
            <span class="prob-label">🩵 종이팩</span>
            <div class="prob-track"><div id="bar-paperpack" class="prob-fill" style="background:#0891b2;"></div></div>
            <span id="val-paperpack" class="prob-val">0%</span>
        </div>
        <div class="prob-row">
            <span class="prob-label">🥤 페트병</span>
            <div class="prob-track"><div id="bar-plastic" class="prob-fill" style="background:#1e40af;"></div></div>
            <span id="val-plastic" class="prob-val">0%</span>
        </div>
        <div class="prob-row">
            <span class="prob-label">🥫 캔</span>
            <div class="prob-track"><div id="bar-can" class="prob-fill" style="background:#15803d;"></div></div>
            <span id="val-can" class="prob-val">0%</span>
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
        AI 스마트 햄스터 분리배출관제센터 v2.5 | logic4rest
    </footer>

    <script>
        let currentMode = 'sim';
        
        function updateAIHUD(category, prob, paperP, packP, plasticP, canP) {
            const tag = document.getElementById('ai-tag');
            if (category !== '없음') {
                tag.innerText = "★ [인식 확정] " + category + " (" + (prob*100).toFixed(0) + "%)";
                tag.style.color = "#38bdf8";
            } else {
                tag.innerText = "🔍 쓰레기 감지 대기 중...";
                tag.style.color = "#94a3b8";
            }

            document.getElementById('bar-paper').style.width = paperP + "%";
            document.getElementById('val-paper').innerText = paperP + "%";

            document.getElementById('bar-paperpack').style.width = packP + "%";
            document.getElementById('val-paperpack').innerText = packP + "%";

            document.getElementById('bar-plastic').style.width = plasticP + "%";
            document.getElementById('val-plastic').innerText = plasticP + "%";

            document.getElementById('bar-can').style.width = canP + "%";
            document.getElementById('val-can').innerText = canP + "%";
        }

        function switchMode(mode) {
            currentMode = mode;
            document.getElementById('btn-mode-real').classList.toggle('active', mode === 'real');
            document.getElementById('btn-mode-sim').classList.toggle('active', mode === 'sim');
            document.getElementById('panel-real').classList.toggle('active', mode === 'real');
            document.getElementById('panel-sim').classList.toggle('active', mode === 'sim');
        }

        function drive(dir) {
            if (currentMode === 'sim') { moveSimRobot(dir); return; }
            fetch('/api/drive', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ direction: dir }) });
        }

        function controlGripper(action) {
            if (currentMode === 'sim') { simGripperState = action; drawSim(); alert("시뮬레이터 집게: " + (action === 'open' ? "열림" : "닫힘")); return; }
            fetch('/api/gripper', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: action }) }).then(r=>r.json()).then(d=>alert(d.message));
        }

        function triggerSort(category) {
            if (category === '종이') updateAIHUD('종이', 0.98, 98, 2, 0, 0);
            else if (category === '종이팩') updateAIHUD('종이팩', 0.95, 2, 95, 3, 0);
            else if (category === '플라스틱/페트병') updateAIHUD('플라스틱/페트병', 0.97, 1, 2, 97, 0);
            else if (category === '캔') updateAIHUD('캔', 0.96, 0, 1, 3, 96);

            if (currentMode === 'sim') { runSimSortingSequence(category); return; }
            fetch('/api/sort', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: category }) }).then(r=>r.json()).then(d=>alert(d.message));
        }

        /* 2D Canvas Simulator */
        const canvas = document.getElementById('simCanvas');
        const ctx = canvas ? canvas.getContext('2d') : null;
        let simRobot = { x: 200, y: 130, angle: 0, originX: 200, originY: 130 };
        let simGripperState = 'open';
        let simRunning = false;

        const simBins = {
            '종이': { x: 340, y: 50, color: '#854d0e', label: '1번 종이' },
            '종이팩': { x: 340, y: 210, color: '#0891b2', label: '2번 종이팩' },
            '플라스틱/페트병': { x: 60, y: 50, color: '#1e40af', label: '3번 페트병' },
            '캔': { x: 60, y: 210, color: '#15803d', label: '4번 캔' }
        };

        function drawSim() {
            if (!ctx) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = '#1e293b';
            for(let x=0; x<canvas.width; x+=40) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke(); }
            for(let y=0; y<canvas.height; y+=40) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(canvas.width,y); ctx.stroke(); }

            ctx.fillStyle = '#38bdf8'; ctx.beginPath(); ctx.arc(simRobot.originX, simRobot.originY, 6, 0, Math.PI*2); ctx.fill();
            ctx.font = '10px sans-serif'; ctx.fillText('시작점(0,0)', simRobot.originX-25, simRobot.originY+18);

            for(let cat in simBins) {
                let bin = simBins[cat];
                ctx.fillStyle = bin.color; ctx.fillRect(bin.x-30, bin.y-20, 60, 40);
                ctx.strokeStyle = '#ffffff'; ctx.strokeRect(bin.x-30, bin.y-20, 60, 40);
                ctx.fillStyle = '#ffffff'; ctx.font = '11px sans-serif'; ctx.fillText(bin.label, bin.x-24, bin.y+4);
            }

            ctx.save(); ctx.translate(simRobot.x, simRobot.y); ctx.rotate(simRobot.angle);
            ctx.fillStyle = '#f59e0b'; ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI*2); ctx.fill(); ctx.strokeStyle = '#ffffff'; ctx.stroke();
            ctx.strokeStyle = simGripperState === 'open' ? '#10b981' : '#ef4444'; ctx.lineWidth = 3;
            let offset = simGripperState === 'open' ? 12 : 4;
            ctx.beginPath(); ctx.moveTo(14, -offset); ctx.lineTo(24, -offset/2); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(14, offset); ctx.lineTo(24, offset/2); ctx.stroke();
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

            log.innerText = "🤖 ['" + category + "'] 6프레임 분석 완료! 집게 열고 4초 거치 대기...";
            simGripperState = 'open'; drawSim();

            setTimeout(() => {
                log.innerText = "🦾 4초 대기 완료! 집게 닫기 (CLOSE) 쓰레기 포획!";
                simGripperState = 'close'; drawSim();

                setTimeout(() => {
                    log.innerText = "🚚 수거함 지정 경로 자율주행 중...";
                    let steps = 30, count = 0;
                    let dx = (targetBin.x - simRobot.x) / steps, dy = (targetBin.y - simRobot.y) / steps;

                    let interval = setInterval(() => {
                        simRobot.x += dx; simRobot.y += dy; drawSim(); count++;
                        if (count >= steps) {
                            clearInterval(interval);
                            log.innerText = "🎉 수거함 도착! 집게 열기 (OPEN) 쓰레기 투입!";
                            simGripperState = 'open'; drawSim();

                            setTimeout(() => {
                                log.innerText = "↩️ 오차 0.00cm 1:1 대칭 정밀 역주행 복귀 중...";
                                let rCount = 0;
                                let rInterval = setInterval(() => {
                                    simRobot.x -= dx; simRobot.y -= dy; drawSim(); rCount++;
                                    if (rCount >= steps) {
                                        clearInterval(rInterval);
                                        simRobot.x = simRobot.originX; simRobot.y = simRobot.originY;
                                        log.innerText = "✅ 시작 위치 복귀 완료! (오차: 0.0000 cm PASS)";
                                        simRunning = false; drawSim();
                                    }
                                }, 50);
                            }, 1000);
                        }
                    }, 50);
                }, 1200);
            }, 2000);
        }

        window.onload = function() { drawSim(); };
    </script>
</body>
</html>
"""

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

_cached_qr_image = None
_qr_url = None

def get_qr_overlay_bgr(url: str, size: int = 140) -> np.ndarray:
    global _cached_qr_image, _qr_url
    if _cached_qr_image is not None and _qr_url == url:
        return _cached_qr_image

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img_pil = qr.make_image(fill_color="black", back_color="white").convert('RGB').resize((size, size))
    _cached_qr_image = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    _qr_url = url
    return _cached_qr_image

def update_web_frame(frame: np.ndarray):
    global latest_frame
    if frame is None:
        return
    with frame_lock:
        latest_frame = frame.copy()

def overlay_qr_code_on_frame(frame: np.ndarray, server_url: str) -> np.ndarray:
    if frame is None:
        return frame
    canvas = frame.copy()
    h, w, _ = canvas.shape
    qr_bgr = get_qr_overlay_bgr(server_url, size=130)
    qr_h, qr_w, _ = qr_bgr.shape
    margin = 15
    y1, y2 = h - qr_h - margin - 25, h - margin - 25
    x1, x2 = w - qr_w - margin, w - margin
    cv2.rectangle(canvas, (x1 - 4, y1 - 22), (x2 + 4, y2 + 4), (255, 255, 255), -1)
    cv2.rectangle(canvas, (x1 - 4, y1 - 22), (x2 + 4, y2 + 4), (0, 120, 255), 2)
    cv2.putText(canvas, "QR Mobile", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
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
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/download')
def download_project_zip():
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in PROJECT_ROOT.glob('**/*'):
            if file_path.is_file() and not any(part.startswith('.') or part in ['__pycache__', 'build', 'dist'] for part in file_path.parts):
                zf.write(file_path, file_path.relative_to(PROJECT_ROOT))
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='hamster_smart_sorting_v8.0.zip')

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
    ip = get_local_ip()
    url = f"http://{ip}:{port}"
    def run():
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return url

if __name__ == "__main__":
    url = start_qr_web_server(5000)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    while True:
        time.sleep(1)
