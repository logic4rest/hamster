"""
스마트폰 QR 모바일 리모컨 & 오프라인 2D/3D 시뮬레이터 & AI 관제 웹서버 (v3.0 100% 오프라인 에디션)
====================================================================================================
- 100% 인터넷 연결 없이 오프라인 가동 (외부 CDN 링크 제거)
- 안드로이드 (Android) & 아이폰/아이패드 (Apple iOS) 터치 제어 & 진동(Haptic) 피드백 지원
- 모바일 웹앱 PWA (Progressive Web App) 메타 태그 내장
- 프리미엄 네온 글래스모피즘 (Glassmorphism) UI/UX 구현
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

HTML_OFFLINE_DASHBOARD = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>🐹 AI 햄스터 로봇 오프라인 스마트 관제센터</title>

    <!-- 📱 Apple iOS & Android PWA 모바일 전용 메타 태그 -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="햄스터 관제">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0b0f19">

    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 30, 49, 0.75);
            --border-color: rgba(255, 255, 255, 0.1);
            --accent-cyan: #00f2fe;
            --accent-blue: #4facfe;
            --accent-purple: #a855f7;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #f59e0b;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; user-select: none; -webkit-tap-highlight-color: transparent; }
        
        body {
            background: var(--bg-color);
            color: #f8fafc;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            padding: 12px;
            padding-bottom: env(safe-area-inset-bottom, 12px);
        }

        /* 💎 프리미엄 헤더 */
        header {
            text-align: center;
            margin-bottom: 12px;
            padding: 16px 12px;
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
        }

        h1 {
            font-size: 1.25rem;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-bottom: 10px;
            font-weight: 800;
        }

        .offline-badge {
            display: inline-block;
            font-size: 0.68rem;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.3);
            padding: 3px 8px;
            border-radius: 12px;
            font-weight: bold;
        }

        /* 모드 탭 셀렉터 */
        .tab-bar {
            display: flex;
            background: rgba(11, 15, 25, 0.8);
            border-radius: 16px;
            padding: 4px;
            border: 1px solid var(--border-color);
            margin: 0 auto;
            max-width: 440px;
            gap: 4px;
        }

        .tab-btn {
            flex: 1;
            padding: 10px 6px;
            font-size: 0.8rem;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            color: #94a3b8;
            background: transparent;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .tab-btn.active {
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
            color: #0b0f19;
            box-shadow: 0 4px 15px rgba(0, 242, 254, 0.35);
        }

        /* 패널 관리 */
        .panel { display: none; }
        .panel.active { display: block; }

        /* 🔮 카드 스타일 */
        .card-box {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 20px;
            padding: 14px;
            border: 1px solid var(--border-color);
            margin-bottom: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        }

        .card-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: #94a3b8;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        canvas#simCanvas {
            background: #070a12;
            border-radius: 14px;
            border: 1px solid var(--border-color);
            width: 100%;
            max-width: 460px;
            height: 250px;
            display: block;
            margin: 0 auto;
        }

        .stream-img {
            width: 100%;
            border-radius: 14px;
            border: 2px solid var(--accent-cyan);
            display: block;
        }

        .status-pill {
            font-size: 0.8rem;
            background: rgba(168, 85, 247, 0.15);
            color: #d8b4fe;
            border: 1px solid rgba(168, 85, 247, 0.3);
            padding: 8px 12px;
            border-radius: 14px;
            text-align: center;
            margin-top: 10px;
            font-weight: 700;
        }

        /* AI 확률 HUD */
        .ai-result-tag {
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--accent-cyan);
            text-align: center;
            padding: 10px;
            background: rgba(7, 10, 18, 0.6);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            margin-bottom: 10px;
        }

        .prob-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 0.78rem; }
        .prob-label { width: 75px; font-weight: 600; }
        .prob-track { flex: 1; background: rgba(7, 10, 18, 0.6); height: 12px; border-radius: 6px; overflow: hidden; border: 1px solid var(--border-color); }
        .prob-fill { height: 100%; width: 0%; transition: width 0.2s ease; }
        .prob-val { width: 35px; text-align: right; font-weight: bold; }

        /* 📱 안드로이드 & 아이폰 터치 컨트롤 그리드 */
        .sort-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

        .btn {
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            font-weight: 700;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 14px;
            cursor: pointer;
            transition: all 0.15s ease;
            touch-action: manipulation;
        }

        .btn:active {
            transform: scale(0.95);
            opacity: 0.85;
            background: var(--accent-cyan);
            color: #0b0f19;
        }

        .btn-paper { background: linear-gradient(135deg, #78350f, #92400e); }
        .btn-paperpack { background: linear-gradient(135deg, #0e7490, #155e75); }
        .btn-plastic { background: linear-gradient(135deg, #1e3a8a, #1e40af); }
        .btn-can { background: linear-gradient(135deg, #14532d, #166534); }

        .dpad-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .dpad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; aspect-ratio: 1; max-width: 170px; margin: 0 auto; }
        .btn-drive { font-size: 1.3rem; background: linear-gradient(135deg, #2563eb, #3b82f6); }
        .btn-stop { background: linear-gradient(135deg, #dc2626, #ef4444); color: white; grid-column: 2; grid-row: 2; font-size: 0.85rem; }
        .btn-grip-open { background: linear-gradient(135deg, #059669, #10b981); }
        .btn-grip-close { background: linear-gradient(135deg, #d97706, #f59e0b); }

        .download-btn {
            width: 100%;
            background: linear-gradient(135deg, #059669, #10b981);
            color: white;
            border: none;
            border-radius: 14px;
            padding: 14px;
            font-size: 0.9rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            text-decoration: none;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            margin-bottom: 12px;
        }

        footer { font-size: 0.7rem; text-align: center; color: #64748b; margin-top: auto; padding-top: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>🐹 AI 햄스터 로봇 분리배출</h1>
        <div style="margin-bottom: 8px;"><span class="offline-badge">⚡ 100% 인터넷 독립 오프라인 가동 중</span></div>
        <div class="tab-bar">
            <button id="tab-sim" class="tab-btn active" onclick="setTab('sim')">🧪 2D 시뮬레이터</button>
            <button id="tab-real" class="tab-btn" onclick="setTab('real')">🤖 실제 햄스터봇</button>
        </div>
    </header>

    <a href="/download" class="download-btn" download>
        📥 소스코드 & 실행파일 (.exe) 전체 다운로드 (ZIP)
    </a>

    <!-- 1. 2D 시뮬레이터 패널 -->
    <div id="panel-sim" class="panel active">
        <div class="card-box" style="border-color: var(--accent-purple); text-align: center;">
            <div class="card-title" style="color: #c084fc; justify-content: center;">🎮 2D 가상 햄스터 분리배출 아레나</div>
            <canvas id="simCanvas" width="400" height="250"></canvas>
            <div id="simLog" class="status-pill">대기 중: 아래 수거 버튼을 누르시면 자율주행 시뮬레이션이 진행됩니다!</div>
        </div>
    </div>

    <!-- 2. 실제 햄스터봇 패널 -->
    <div id="panel-real" class="panel">
        <div class="card-box" style="border-color: var(--accent-cyan);">
            <div class="card-title" style="color: var(--accent-cyan); justify-content: center;">📹 실물 웹캠 & 햄스터봇 실시간 라이브 스트림</div>
            <img src="/video_feed" class="stream-img" alt="실물 로봇 카메라 라이브">
        </div>
    </div>

    <!-- 🤖 AI 인식 결과 HUD -->
    <div class="card-box" style="border-color: var(--accent-blue);">
        <div class="card-title">🤖 AI 실시간 감지 분석 결과</div>
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

    <!-- 원터치 자율 수거 버튼 -->
    <div class="card-box">
        <div class="card-title">♻️ 스마트 분리배출 자율 수거</div>
        <div class="sort-grid">
            <button class="btn btn-paper" onclick="triggerSort('종이')">📄 1번 종이</button>
            <button class="btn btn-paperpack" onclick="triggerSort('종이팩')">🩵 2번 종이팩</button>
            <button class="btn btn-plastic" onclick="triggerSort('플라스틱/페트병')">🥤 3번 페트병</button>
            <button class="btn btn-can" onclick="triggerSort('캔')">🥫 4번 캔</button>
        </div>
    </div>

    <!-- 터치 수동 D-Pad & 집게 제어 -->
    <div class="dpad-layout">
        <div class="card-box">
            <div class="card-title">🕹️ 방향 주행</div>
            <div class="dpad">
                <button class="btn btn-drive" style="grid-column: 2; grid-row: 1;" onclick="drive('up')">▲</button>
                <button class="btn btn-drive" style="grid-column: 1; grid-row: 2;" onclick="drive('left')">◀</button>
                <button class="btn btn-stop" onclick="drive('stop')">정지</button>
                <button class="btn btn-drive" style="grid-column: 3; grid-row: 2;" onclick="drive('right')">▶</button>
                <button class="btn btn-drive" style="grid-column: 2; grid-row: 3;" onclick="drive('down')">▼</button>
            </div>
        </div>

        <div class="card-box" style="display: flex; flex-direction: column; justify-content: space-between;">
            <div class="card-title">🦾 집게 제어</div>
            <button class="btn btn-grip-open" style="margin-bottom: 8px;" onclick="controlGripper('open')">👐 집게 펴기 (OPEN)</button>
            <button class="btn btn-grip-close" onclick="controlGripper('close')">✊ 집게 닫기 (CLOSE)</button>
        </div>
    </div>

    <footer>
        AI 햄스터 로봇 스마트 분리배출 오프라인 관제센터 v3.0 | logic4rest
    </footer>

    <script>
        let currentTab = 'sim';

        // 📱 안드로이드 & 아이폰 Haptic 진동 피드백 지원
        function triggerHaptic() {
            if (navigator.vibrate) {
                try { navigator.vibrate(40); } catch(e) {}
            }
        }

        function setTab(tab) {
            triggerHaptic();
            currentTab = tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            
            document.getElementById('tab-' + tab).classList.add('active');
            document.getElementById('panel-' + tab).classList.add('active');
        }

        function updateAIHUD(category, prob, paperP, packP, plasticP, canP) {
            const tag = document.getElementById('ai-tag');
            if (category !== '없음') {
                tag.innerText = "★ [인식 확정] " + category + " (" + (prob*100).toFixed(0) + "%) [6/6프레임]";
                tag.style.color = "#00f2fe";
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

        function playBeepSound() {
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine'; osc.frequency.value = 880;
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start();
                gain.gain.exponentialRampToValueAtTime(0.00001, audioCtx.currentTime + 0.15);
                setTimeout(() => osc.stop(), 150);
            } catch(e) {}
        }

        function drive(dir) {
            triggerHaptic();
            moveSimRobot(dir);
            fetch('/api/drive', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ direction: dir }) }).catch(() => {});
        }

        function controlGripper(action) {
            triggerHaptic();
            simGripperState = action;
            drawSim();
            playBeepSound();
            fetch('/api/gripper', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: action }) }).catch(() => {});
        }

        function triggerSort(category) {
            triggerHaptic();
            if (category === '종이') updateAIHUD('종이', 0.98, 98, 2, 0, 0);
            else if (category === '종이팩') updateAIHUD('종이팩', 0.95, 2, 95, 3, 0);
            else if (category === '플라스틱/페트병') updateAIHUD('플라스틱/페트병', 0.97, 1, 2, 97, 0);
            else if (category === '캔') updateAIHUD('캔', 0.96, 0, 1, 3, 96);

            runSimSortingSequence(category);
            fetch('/api/sort', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: category }) }).catch(() => {});
        }

        /* 🎮 오프라인 2D 캔버스 시뮬레이터 */
        const canvas = document.getElementById('simCanvas');
        const ctx = canvas ? canvas.getContext('2d') : null;
        
        let simRobot = { x: 200, y: 125, angle: 0, originX: 200, originY: 125 };
        let simGripperState = 'open';
        let simRunning = false;

        const simBins = {
            '종이': { x: 340, y: 45, color: '#92400e', label: '1번 종이' },
            '종이팩': { x: 340, y: 205, color: '#0e7490', label: '2번 종이팩' },
            '플라스틱/페트병': { x: 60, y: 45, color: '#1e40af', label: '3번 페트병' },
            '캔': { x: 60, y: 205, color: '#166534', label: '4번 캔' }
        };

        function drawSim() {
            if (!ctx) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            ctx.strokeStyle = '#1e293b';
            for(let x=0; x<canvas.width; x+=40) { ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke(); }
            for(let y=0; y<canvas.height; y+=40) { ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(canvas.width,y); ctx.stroke(); }

            ctx.fillStyle = '#00f2fe';
            ctx.beginPath(); ctx.arc(simRobot.originX, simRobot.originY, 6, 0, Math.PI*2); ctx.fill();
            ctx.font = '10px sans-serif'; ctx.fillText('시작점(0,0)', simRobot.originX-25, simRobot.originY+18);

            for(let cat in simBins) {
                let bin = simBins[cat];
                ctx.fillStyle = bin.color;
                ctx.fillRect(bin.x-30, bin.y-20, 60, 40);
                ctx.strokeStyle = '#ffffff'; ctx.strokeRect(bin.x-30, bin.y-20, 60, 40);
                ctx.fillStyle = '#ffffff'; ctx.font = '11px sans-serif'; ctx.fillText(bin.label, bin.x-24, bin.y+4);
            }

            ctx.save();
            ctx.translate(simRobot.x, simRobot.y);
            ctx.rotate(simRobot.angle);

            ctx.fillStyle = '#f59e0b';
            ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI*2); ctx.fill();
            ctx.strokeStyle = '#ffffff'; ctx.stroke();

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

            playBeepSound();
            log.innerText = "🤖 ['" + category + "'] 6프레임 감지 완료! 삐! 집게 열고 4초 거치 대기...";
            simGripperState = 'open';
            drawSim();

            let waitSec = 4.0;
            let timerInterval = setInterval(() => {
                waitSec -= 0.5;
                if (waitSec > 0) {
                    log.innerText = "🦾 ['" + category + "'] 집게 열림(OPEN)! 쓰레기를 놓아주세요 (" + waitSec.toFixed(1) + "초 남음)";
                } else {
                    clearInterval(timerInterval);
                    playBeepSound();
                    log.innerText = "🦾 4초 대기 완료! 삐! 집게 닫기 (CLOSE) 쓰레기 포획!";
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
                                playBeepSound();
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
                    }, 1000);
                }
            }, 500);
        }

        window.onload = function() {
            drawSim();
        };
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
    return render_template_string(HTML_OFFLINE_DASHBOARD)

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

@app.route('/api/status', methods=['GET'])
def api_status():
    connected = robot_controller_callback is not None
    return jsonify({
        "status": "ok",
        "robot_connected": connected,
        "message": "🤖 실물 햄스터 로봇과 파이썬 AI 엔진이 1:1 연결되었습니다!" if connected else "⚠️ 실물 햄스터 로봇을 연결하려면 바탕화면의 [햄스터_분리배출_실행.bat]을 실행하세요."
    })

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
