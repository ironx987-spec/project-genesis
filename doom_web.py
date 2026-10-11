"""
doom_web.py — Веб-интерфейс KAIROS.
Gemini-стиль, 2 вкладки, анимации, защита.
"""

from flask import Flask, render_template_string, request, jsonify
import os

app = Flask(__name__)


# ============================================================
#  НАСТРОЙКИ
# ============================================================

# PIN читается из ~/.doom_pin (создаётся вручную или через настройки)
def _load_pin():
    import os
    path = os.path.expanduser("~/.doom_pin")
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "doom"

PIN_DEFAULT = _load_pin()
GLOBAL_BRIDGE = None
GLOBAL_CORE = None

# ============================================================
#  HTML + CSS + JS
# ============================================================

HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#000000">
<script>window.GENESIS_PIN = "{{PIN}}";</script>
<link rel="manifest" href="/static/manifest.json">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="GENESIS">
<meta name="mobile-web-app-capable" content="yes">
<title>GENESIS</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    width: 100%; height: 100%;
    background: #000;
    color: #e0e0e0;
    font-family: -apple-system, 'Inter', 'SF Pro', system-ui, sans-serif;
    overflow: hidden;
    -webkit-tap-highlight-color: transparent;
  }

  /* === ОСНОВНОЙ КОНТЕЙНЕР === */
  .app {
    width: 100%; height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
    background: #000;
    overflow: hidden;
    transition: filter 0.5s;
  }

  /* Прямое свечение снизу */
  .glow-curve {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 35%;
    pointer-events: none;
    z-index: 0;
  }
  .glow-curve.normal {
    display: block;
    background: linear-gradient(180deg, 
      rgba(58,138,255,0) 0%, 
      rgba(58,138,255,0.08) 30%,
      rgba(58,138,255,0.20) 60%,
      rgba(58,138,255,0.45) 100%);
  }
  .glow-curve.defense {
    display: none;
    background: linear-gradient(180deg, 
      rgba(255,58,58,0) 0%, 
      rgba(255,58,58,0.08) 30%,
      rgba(255,58,58,0.20) 60%,
      rgba(255,58,58,0.45) 100%);
  }
  .app.defense-mode .glow-curve.normal { display: none !important; }
  .app.defense-mode .glow-curve.defense { display: block !important; }

  /* === ВЕРХНЯЯ ПАНЕЛЬ === */
  .topbar {
    position: absolute;
    top: 0; left: 0; right: 0;
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 10;
    font-size: 16px;
    color: #e0e0e0;
    opacity: 1;
    transition: opacity 0.4s;
  }
  .topbar-left {
    display: flex; align-items: center; gap: 12px;
  }
  .burger {
    width: 24px; height: 24px;
    display: flex; flex-direction: column; justify-content: center; gap: 4px;
    cursor: pointer;
  }
  .burger div {
    width: 20px; height: 2px; background: #e0e0e0; border-radius: 2px;
    transition: 0.3s;
  }
  .tab-title {
    font-size: 16px;
    color: #e0e0e0;
    cursor: pointer;
    display: flex; align-items: center; gap: 4px;
  }
  .topbar-right {
    display: flex; align-items: center; gap: 14px;
  }
  .icon-btn {
    width: 24px; height: 24px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    font-size: 16px;
    transition: 0.3s;
    opacity: 0.9;
  }
  .icon-btn:active { transform: scale(0.9); }

  /* === МЕНЮ ВКЛАДОК === */
  .tab-menu {
    position: absolute;
    top: 60px; left: 20px;
    background: #1a1a1a;
    border-radius: 16px;
    padding: 8px 0;
    min-width: 240px;
    z-index: 30;
    opacity: 0;
    pointer-events: none;
    transform: translateY(-10px);
    transition: opacity 0.3s, transform 0.3s;
    box-shadow: 0 10px 40px rgba(0,0,0,0.8);
  }
  .tab-menu.open {
    opacity: 1;
    pointer-events: auto;
    transform: translateY(0);
  }
  .tab-item {
    padding: 14px 20px;
    font-size: 16px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: space-between;
    transition: background 0.2s;
  }
  .tab-item:hover { background: #2a2a2a; }
  .tab-item.active { color: #3a8aff; }
  .tab-item .check { color: #3a8aff; font-weight: bold; }

  /* === ГЛАВНАЯ ОБЛАСТЬ === */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    padding: 80px 20px 120px;
  }

  /* === ЗВЕЗДА === */
  .star-container {
    width: 100px; height: 100px;
    display: flex; align-items: center; justify-content: center;
    transition: opacity 0.5s, transform 0.5s;
    position: absolute;
    top: 45%;
    transform: translateY(-50%);
  }
  .star-container.hidden {
    opacity: 0;
    pointer-events: none;
    transform: translateY(-50%) scale(0.5);
  }
  .star-container.defense {
    animation: spin360 1s ease-out forwards;
  }
  /* Защита: звезда становится красной и пульсирует по контуру */
  .star-container.defense .star-svg {
    animation: none;
  }
  .star-container.defense .star-svg path {
    fill: #ff2a2a !important;
  }
  .star-container.defense.pulsing .star-svg {
    animation: pulseRedContour 1.5s ease-in-out infinite !important;
  }

  @keyframes spin360 {
    from { transform: translateY(-50%) rotate(0deg); }
    to { transform: translateY(-50%) rotate(180deg); }
  }
  @keyframes pulseRedContour {
    0%, 100% {
      filter: drop-shadow(0 0 6px #ff2a2a) drop-shadow(0 0 14px #ff2a2a);
    }
    50% {
      filter: drop-shadow(0 0 18px #ff2a2a) drop-shadow(0 0 40px #ff2a2a);
    }
  }

  .star-svg {
    width: 100%; height: 100%;
    animation: starPulseNormal 3s ease-in-out infinite;
  }
  @keyframes starPulseNormal {
    0%, 100% { 
      filter: drop-shadow(0 0 12px #6a4aff) drop-shadow(0 0 24px #3a8aff);
    }
    50% { 
      filter: drop-shadow(0 0 20px #6a4aff) drop-shadow(0 0 40px #3a8aff);
    }
  }

  /* === ТОЧКИ ЗАГРУЗКИ (орбита + схлопывание) === */
  .dots-container {
    position: absolute;
    top: 45%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 120px;
    height: 120px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.4s;
  }
  .dots-container.active {
    opacity: 1;
  }
  .dot {
    position: absolute;
    top: 50%; left: 50%;
    width: 16px; height: 16px;
    margin: -8px 0 0 -8px;
    border-radius: 50%;
    background: #3a8aff;
    box-shadow: 0 0 15px #3a8aff, 0 0 30px #3a8aff;
    will-change: transform;
  }

  /* === ТЕКСТ (приветствие / ответ) === */
  .message {
    position: absolute;
    top: 55%;
    width: 100%;
    padding: 0 24px;
    text-align: center;
    font-size: 28px;
    font-weight: 400;
    color: #e0e0e0;
    line-height: 1.3;
    transition: opacity 0.5s, transform 0.5s;
    word-wrap: break-word;
  }
  .message.hidden {
    opacity: 0;
    transform: translateY(-20px);
    pointer-events: none;
  }

  /* === ВОЛНА МИКРОФОНА === */
  .mic-wave {
    position: absolute;
    top: 45%;
    transform: translateY(-50%);
    width: 100%;
    height: 120px;
    display: none;
    align-items: center;
    justify-content: center;
    gap: 3px;
  }
  .mic-wave.active {
    display: flex;
  }
  .wave-bar {
    width: 3px;
    background: #3a8aff;
    border-radius: 3px;
    height: 6px;
    box-shadow: 0 0 10px #3a8aff;
    transition: height 0.06s linear, opacity 0.06s linear;
    opacity: 0.6;
  }

  /* === НИЖНЯЯ ПАНЕЛЬ ВВОДА === */
  .input-bar {
    position: fixed;
    bottom: 16px;
    left: 12px; right: 12px;
    background: #1a1a1a;
    border-radius: 36px;
    padding: 22px 18px;
    display: flex;
    align-items: center;
    gap: 8px;
    z-index: 50;
  }
  .input-bar input {
    flex: 1;
    min-width: 0;
    background: transparent;
    border: none;
    outline: none;
    color: #e0e0e0;
    font-size: 18px;
    font-family: inherit;
  }
  .input-bar input::placeholder { color: #666; }
  .input-icon {
    width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    color: #999;
    transition: 0.3s;
    flex-shrink: 0;
  }
  .input-icon:active { transform: scale(0.9); }
  .input-icon.recording { color: #ff3a3a; }

  /* === ЗАЩИТА === */
  .app.defense-mode {
    background: #000;
  }

  .defense-lock {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.85);
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 100;
    gap: 20px;
    padding: 40px;
    backdrop-filter: blur(10px);
  }
  .defense-lock.active { display: flex; }
  .defense-lock h2 {
    font-size: 20px;
    color: #ff3a3a;
    margin-bottom: 10px;
    letter-spacing: 2px;
  }
  .pin-input {
    background: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 12px;
    padding: 14px 20px;
    color: #e0e0e0;
    font-size: 20px;
    text-align: center;
    letter-spacing: 8px;
    width: 200px;
    font-family: monospace;
  }
  .pin-btn {
    background: #3a8aff;
    color: #fff;
    border: none;
    border-radius: 12px;
    padding: 12px 32px;
    font-size: 16px;
    cursor: pointer;
    font-family: inherit;
    transition: 0.3s;
  }
  .pin-btn:active { transform: scale(0.95); }

  /* === 3D-ВКЛАДКА (заглушка) === */
  .manual-view {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: none;
    flex-direction: column;
    padding: 80px 20px 100px;
    gap: 20px;
  }
  .manual-view.active { display: flex; }
  .manual-view .three-d {
    flex: 1;
    background: transparent;
    border-radius: 16px;
    overflow: hidden;
    position: relative;
    touch-action: none;
    -webkit-user-select: none;
    user-select: none;
  }
  .manual-view .three-d canvas {
    touch-action: none !important;
  }
  .manual-view .three-d canvas {
    display: block;
    width: 100% !important;
    height: 100% !important;
  }

  /* === СКРЫТИЕ ВЕРХНЕЙ ПАНЕЛИ ПРИ ПЕЧАТИ === */
  body.typing .topbar { opacity: 0; pointer-events: none; }

  /* === ПЛАВНАЯ СМЕНА ВКЛАДОК === */
  .slide-left { animation: slideLeft 0.35s ease-out; }
  .slide-right { animation: slideRight 0.35s ease-out; }
  @keyframes slideLeft {
    from { transform: translateX(40px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  @keyframes slideRight {
    from { transform: translateX(-40px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }

</style>

<!-- Three.js + OrbitControls (0.140 — есть examples/js) -->
<script src="https://cdn.jsdelivr.net/npm/three@0.140.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.140.0/examples/js/controls/OrbitControls.js"></script>

</head>
<body>

<div class="app" id="app">

  <!-- СВЕЧЕНИЕ (прямое) -->
  <div class="glow-curve normal"></div>
  <div class="glow-curve defense"></div>

  <!-- ВЕРХНЯЯ ПАНЕЛЬ -->
  <div class="topbar" id="topbar">
    <div class="topbar-left">
      <div class="burger" onclick="toggleMenu()">
        <div></div><div></div><div></div>
      </div>
      <div class="tab-title" onclick="toggleMenu()">
        <span id="tabTitle">Основное</span>
        <span>⌄</span>
      </div>
    </div>
    <div class="topbar-right">
      <div class="icon-btn" onclick="newChat()" title="Новый чат">↻</div>
      <div class="icon-btn" onclick="showHistory()" title="История">⏱</div>
      <div class="icon-btn" id="soundBtn" onclick="toggleSound()" title="Звук">🔊</div>
      <div class="icon-btn" id="defenseBtn" onclick="toggleDefense()" title="Защита">🔴</div>
    </div>
  </div>

  <!-- МЕНЮ ВКЛАДОК -->
  <div class="tab-menu" id="tabMenu">
    <div class="tab-item active" onclick="switchTab(0)" id="tabItem0">
      <span>Основное</span>
      <span class="check">✓</span>
    </div>
    <div class="tab-item" onclick="switchTab(1)" id="tabItem1">
      <span>Управление</span>
      <span class="check" style="display:none">✓</span>
    </div>
  </div>

  <!-- ВКЛАДКА 1 — ОСНОВНОЕ -->
  <div class="main" id="mainView">
    <div class="star-container" id="starContainer">
      <svg class="star-svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="starGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#ff3a3a"/>
            <stop offset="50%" stop-color="#6a4aff"/>
            <stop offset="100%" stop-color="#3a8aff"/>
          </linearGradient>
        </defs>
        <path d="M50 5 Q55 45 95 50 Q55 55 50 95 Q45 55 5 50 Q45 45 50 5 Z" fill="url(#starGrad)"/>
      </svg>
    </div>

    <div class="dots-container" id="dotsContainer">
      <div class="dot" id="dot0"></div>
      <div class="dot" id="dot1"></div>
      <div class="dot" id="dot2"></div>
    </div>

    <div class="message" id="message">Сэр, системы готовы</div>
    <audio id="ttsAudio" style="display:none"></audio>

    <div class="mic-wave" id="micWave">
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
    </div>
  </div>

  <!-- ВКЛАДКА 2 — УПРАВЛЕНИЕ -->
  <div class="manual-view" id="manualView">
    <div class="three-d" id="threeCanvas"></div>

      <!-- ПАНЕЛЬ РУЧНОГО УПРАВЛЕНИЯ (6-DOF) -->
      <div id="manual-controls" class="manual-panel">
        <div class="manual-title">MANUAL CONTROL (6 DOF)</div>

        <div class="slider-row">
          <label>BASE</label>
          <input type="range" id="sl-base" min="0" max="180" value="90">
          <span id="val-base">90</span>
        </div>
        <div class="slider-row">
          <label>SHOULDER</label>
          <input type="range" id="sl-shoulder" min="15" max="165" value="45">
          <span id="val-shoulder">45</span>
        </div>
        <div class="slider-row">
          <label>ELBOW</label>
          <input type="range" id="sl-elbow" min="30" max="150" value="135">
          <span id="val-elbow">135</span>
        </div>
        <div class="slider-row">
          <label>WRIST P</label>
          <input type="range" id="sl-wristP" min="20" max="160" value="60">
          <span id="val-wristP">60</span>
        </div>
        <div class="slider-row">
          <label>WRIST R</label>
          <input type="range" id="sl-wristR" min="0" max="180" value="90">
          <span id="val-wristR">90</span>
        </div>
        <div class="slider-row">
          <label>GRIPPER</label>
          <input type="range" id="sl-gripper" min="10" max="100" value="30">
          <span id="val-gripper">30</span>
        </div>

        <button id="btn-home" class="btn-home">HOME</button>
      </div>

      <style>
        .manual-panel {
          margin-top: 12px;
          padding: 14px 16px;
          background: rgba(20, 30, 50, 0.75);
          border: 1px solid rgba(58, 138, 255, 0.3);
          border-radius: 12px;
          color: #c8dcff;
          font-family: monospace;
        }
        .manual-title {
          font-size: 13px;
          letter-spacing: 2px;
          color: #6a9aff;
          margin-bottom: 12px;
          text-align: center;
        }
        .slider-row {
          display: grid;
          grid-template-columns: 90px 1fr 40px;
          align-items: center;
          gap: 10px;
          margin-bottom: 8px;
          font-size: 12px;
        }
        .slider-row label { color: #6a9aff; }
        .slider-row span { color: #fff; text-align: right; }
        .slider-row input[type="range"] {
          -webkit-appearance: none;
          height: 6px;
          background: linear-gradient(90deg, #1a3a6a, #3a8aff);
          border-radius: 3px;
          outline: none;
        }
        .slider-row input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          width: 18px;
          height: 18px;
          background: #3a8aff;
          border: 2px solid #fff;
          border-radius: 50%;
          box-shadow: 0 0 8px #3a8aff;
          cursor: pointer;
        }
        .btn-home {
          width: 100%;
          margin-top: 10px;
          padding: 10px;
          background: rgba(58, 138, 255, 0.15);
          border: 1px solid #3a8aff;
          color: #c8dcff;
          font-family: monospace;
          letter-spacing: 2px;
          border-radius: 8px;
          cursor: pointer;
        }
        .btn-home:active { background: rgba(58, 138, 255, 0.35); }
      </style>

  </div>

  <!-- НИЖНЯЯ ПАНЕЛЬ -->
  <div class="input-bar">
    <div class="input-icon" onclick="newChat()">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
      </svg>
    </div>
    <input type="text" id="userInput" placeholder="Спросить KAIROSа..." 
           onfocus="onInputFocus()" onblur="onInputBlur()"
           onkeydown="if(event.key==='Enter') sendMessage()">
    <div class="input-icon" id="micBtn" onclick="toggleMic()">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="2" width="6" height="12" rx="3"/>
        <path d="M5 10a7 7 0 0 0 14 0"/>
        <line x1="12" y1="17" x2="12" y2="22"/>
        <line x1="8" y1="22" x2="16" y2="22"/>
      </svg>
    </div>
    <div class="input-icon" onclick="sendMessage()">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="19" x2="12" y2="5"/>
        <polyline points="5 12 12 5 19 12"/>
      </svg>
    </div>
  </div>

  <!-- ЗАЩИТА (PIN) -->
  <div class="defense-lock" id="defenseLock">
    <h2>РЕЖИМ ЗАЩИТЫ</h2>
    <p style="color:#999;font-size:14px">Введите PIN для снятия</p>
    <input type="password" class="pin-input" id="pinInput" maxlength="6" placeholder="••••">
    <button class="pin-btn" onclick="unlockDefense()">Снять</button>
  </div>

</div>

<script>
// === СОСТОЯНИЕ ===
let state = {
  tab: 0,
  soundOn: true,
  defense: false,
  recording: false,
  thinking: false,
};

// === УТИЛИТЫ ===
function setMessage(text) {
  const m = document.getElementById('message');
  m.textContent = text;
  m.classList.remove('hidden');
}

function hideMessage() {
  document.getElementById('message').classList.add('hidden');
}

// === ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК ===
function toggleMenu() {
  document.getElementById('tabMenu').classList.toggle('open');
}

function switchTab(idx) {
  if (state.defense) return;
  state.tab = idx;
  document.getElementById('tabMenu').classList.remove('open');
  
  const main = document.getElementById('mainView');
  const manual = document.getElementById('manualView');
  const title = document.getElementById('tabTitle');
  const item0 = document.getElementById('tabItem0');
  const item1 = document.getElementById('tabItem1');
  
  if (idx === 0) {
    main.style.display = 'flex';
    manual.classList.remove('active');
    main.classList.add('slide-right');
    title.textContent = 'Основное';
    item0.classList.add('active');
    item1.classList.remove('active');
    item0.querySelector('.check').style.display = 'inline';
    item1.querySelector('.check').style.display = 'none';
  } else {
    main.style.display = 'none';
    manual.classList.add('active');
    manual.classList.add('slide-left');
    title.textContent = 'Управление';
    // Инициализация 3D при первом открытии
    setTimeout(() => {
      initThree();
      setTimeout(resizeThree, 100);
    }, 50);
    item1.classList.add('active');
    item0.classList.remove('active');
    item0.querySelector('.check').style.display = 'none';
    item1.querySelector('.check').style.display = 'inline';
  }
  
  setTimeout(() => {
    main.classList.remove('slide-right');
    manual.classList.remove('slide-left');
  }, 400);
}

// === ВВОД ===
function onInputFocus() {
  document.body.classList.add('typing');
}
function onInputBlur() {
  document.body.classList.remove('typing');
}

// === НОВЫЙ ЧАТ ===
function newChat() {
  if (state.defense) return;
  setMessage('Сэр, системы готовы');
}

// === ИСТОРИЯ ===
function showHistory() {
  if (state.defense) return;
  // TODO: запрос PIN
  setMessage('История: (позже)');
}

// === ЗВУК ===
function toggleSound() {
  state.soundOn = !state.soundOn;
  document.getElementById('soundBtn').textContent = state.soundOn ? '🔊' : '🔈';
}

// === ЗАЩИТА ===
function toggleDefense() {
  if (state.defense) {
    // Уже защита — показать ввод PIN
    document.getElementById('defenseLock').classList.add('active');
    document.getElementById('pinInput').focus();
  } else {
    // Включить защиту
    state.defense = true;
    document.getElementById('app').classList.add('defense-mode');
    const star = document.getElementById('starContainer');
    star.classList.add('defense');
    setTimeout(() => star.classList.add('pulsing'), 1000);
    document.getElementById('micWave').classList.remove('active');
    hideMessage();
  }
}

function unlockDefense() {
  const pin = document.getElementById('pinInput').value;
  if (pin === window.GENESIS_PIN) {
    state.defense = false;
    document.getElementById('defenseLock').classList.remove('active');
    document.getElementById('app').classList.remove('defense-mode');
    const star = document.getElementById('starContainer');
    star.classList.remove('pulsing');
    star.classList.remove('defense');
    document.getElementById('pinInput').value = '';
    setMessage('Сэр, системы готовы');
  } else {
    document.getElementById('pinInput').value = '';
    document.getElementById('pinInput').placeholder = 'Неверно';
    setTimeout(() => {
      document.getElementById('pinInput').placeholder = '••••';
    }, 1500);
  }
}

// === МИКРОФОН + WEB SPEECH API ===
let recognition = null;
let recognitionActive = false;

function initSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    console.warn('[VOICE] Web Speech API не поддерживается');
    return null;
  }
  const rec = new SR();
  rec.lang = 'ru-RU';
  rec.continuous = false;
  rec.interimResults = true;
  rec.maxAlternatives = 1;
  
  rec.onstart = () => {
    console.log('[VOICE] Слушаю...');
  };
  
  rec.onresult = (event) => {
    let interim = '';
    let final = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        final += transcript;
      } else {
        interim += transcript;
      }
    }
    // Показываем промежуточный результат в поле ввода
    const input = document.getElementById('userInput');
    input.value = interim || final;
    
    // Если финал — отправляем
    if (final) {
      stopMic();
      setTimeout(() => sendMessage(), 200);
    }
  };
  
  rec.onerror = (event) => {
    console.error('[VOICE] Ошибка:', event.error);
    if (event.error === 'not-allowed') {
      setMessage('Сэр, разрешите доступ к микрофону.');
    } else if (event.error === 'no-speech') {
      setMessage('Сэр, не услышал.');
    } else if (event.error !== 'aborted') {
      setMessage('Сэр, ошибка распознавания.');
    }
    stopMic();
  };
  
  rec.onend = () => {
    console.log('[VOICE] Конец записи');
    if (recognitionActive) {
      // Если не получили финал — просто сбрасываем
      stopMic();
    }
  };
  
  return rec;
}

// === ВИЗУАЛИЗАЦИЯ ГРОМКОСТИ МИКРОФОНА ===
let _micAudioCtx = null;
let _micAnalyser = null;
let _micStream = null;
let _micRafId = null;

// ПСЕВДО-ВИЗУАЛИЗАЦИЯ (без getUserMedia — чтобы не мешать Web Speech API)
let _fakeWaveId = null;

function startFakeWave() {
  const waveBars = document.querySelectorAll('#micWave .wave-bar');
  const N = waveBars.length;
  const mid = (N - 1) / 2;
  const phases = [];
  const speeds = [];
  for (let i = 0; i < N; i++) {
    phases.push(Math.random() * Math.PI * 2);
    speeds.push(0.08 + Math.random() * 0.06);
  }

  function tick() {
    const t = performance.now() / 1000;
    for (let i = 0; i < N; i++) {
      const dist = Math.abs(i - mid) / mid;
      const shape = 1 - dist * 0.55;
      // Комбинация двух синусов — «живая» волна
      const s = Math.sin(t * 6 * speeds[i] + phases[i]);
      const s2 = Math.sin(t * 3.7 * speeds[i] + phases[i] * 1.7);
      const level = 0.5 + 0.5 * (s * 0.6 + s2 * 0.4);
      const h = 6 + level * 70 * shape;
      const op = 0.5 + level * 0.5;
      waveBars[i].style.height = h.toFixed(1) + 'px';
      waveBars[i].style.opacity = op.toFixed(2);
    }
    _fakeWaveId = requestAnimationFrame(tick);
  }
  tick();
  console.log('[MIC] Псевдо-визуализация запущена.');
}

function stopFakeWave() {
  if (_fakeWaveId) { cancelAnimationFrame(_fakeWaveId); _fakeWaveId = null; }
  const waveBars = document.querySelectorAll('#micWave .wave-bar');
  waveBars.forEach(function(b) { b.style.height = '6px'; b.style.opacity = '0.6'; });
  console.log('[MIC] Псевдо-визуализация остановлена.');
}


function startMic() {
  if (state.defense) return;
  if (recognitionActive) return;
  
  if (!recognition) {
    recognition = initSpeechRecognition();
    if (!recognition) {
      setMessage('Сэр, браузер не поддерживает голос.');
      return;
    }
  }
  
  recognitionActive = true;
  state.recording = true;
  
  const btn = document.getElementById('micBtn');
  const wave = document.getElementById('micWave');
  const star = document.getElementById('starContainer');
  const dots = document.getElementById('dotsContainer');
  
  btn.classList.add('recording');
  wave.classList.add('active');
  star.classList.add('hidden');
  dots.classList.remove('active');
  hideMessage();
  
  try {
    recognition.start();
  } catch (e) {
    console.error('[VOICE] start error:', e);
    stopMic();
    return;
  }

  // Запускаем псевдо-визуализацию (без getUserMedia — не мешает Web Speech API)
  startFakeWave();
}

function stopMic() {
  recognitionActive = false;
  state.recording = false;

  // Останавливаем псевдо-визуализацию
  stopFakeWave();
  
  const btn = document.getElementById('micBtn');
  const wave = document.getElementById('micWave');
  const star = document.getElementById('starContainer');
  
  btn.classList.remove('recording');
  wave.classList.remove('active');
  star.classList.remove('hidden');
  
  if (recognition) {
    try { recognition.stop(); } catch (e) {}
  }
  
  // Если не было финала — вернуть приветствие
  const input = document.getElementById('userInput');
  if (!input.value.trim()) {
    setMessage('Сэр, системы готовы');
  }
}

function toggleMic() {
  if (state.defense) return;
  if (recognitionActive) {
    stopMic();
  } else {
    startMic();
  }
}

// === ОТПРАВКА ===
async function sendMessage() {
  if (state.defense) return;
  const input = document.getElementById('userInput');
  const text = input.value.trim();
  if (!text) return;
  
  input.value = '';
  
  // Показать "думает"
  state.thinking = true;
  const star = document.getElementById('starContainer');
  const dots = document.getElementById('dotsContainer');
  hideMessage();
  star.classList.add('hidden');
  dots.classList.add('active');
  startDotsAnimation();
  
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text})
    });
    const data = await resp.json();
    
    stopDotsAnimation();
    dots.classList.remove('active');
    star.classList.remove('hidden');
    setMessage(data.response || 'Сэр, ответ не получен.');
    // === Синхронизация 3D-модели с позой робота ===
    try {
      const poseResp = await fetch('/api/last_pose');
      const poseData = await poseResp.json();
      if (poseData && poseData.ok && poseData.pose && Object.keys(poseData.pose).length) {
        const pose = poseData.pose;
        if (typeof setJointAngles === 'function') setJointAngles(pose);
        Object.keys(pose).forEach(function(j) {
          const sl = document.getElementById('sl-' + j);
          const val = document.getElementById('val-' + j);
          if (sl && typeof pose[j] === 'number') {
            sl.value = pose[j];
            if (val) val.textContent = pose[j];
          }
        });
        console.log('[POSE] применена:', pose);
      }
    } catch (e) {
      console.warn('[POSE] ошибка:', e);
    }
    
    // Озвучка (если есть mp3 и звук включён)
    if (state.soundOn && data.audio_url) {
      const audio = document.getElementById('ttsAudio');
      audio.src = data.audio_url;
      audio.play().catch(e => console.log('audio err:', e));
    }
  } catch (e) {
    stopDotsAnimation();
    dots.classList.remove('active');
    star.classList.remove('hidden');
    setMessage('Сэр, ошибка связи.');
  }
  state.thinking = false;
}

// === АНИМАЦИЯ ТОЧЕК (орбита → центр → разлёт) ===
let dotsAnimationId = null;
const DOTS_CYCLE_MS = 3000;  // 3 секунды на полный цикл
const DOTS_RADIUS = 40;

function animateDots(ts) {
  if (!state.thinking) return;
  
  const cycle = (ts % DOTS_CYCLE_MS) / DOTS_CYCLE_MS;  // 0..1
  let radius;
  
  // Фаза 1 (0-0.5): орбита, радиус = 40
  // Фаза 2 (0.5-0.75): схлопывание, 40 → 0
  // Фаза 3 (0.75-1.0): разлёт, 0 → 40
  if (cycle < 0.5) {
    radius = DOTS_RADIUS;
  } else if (cycle < 0.75) {
    const p = (cycle - 0.5) / 0.25;  // 0..1
    radius = DOTS_RADIUS * (1 - p);   // ease-out
  } else {
    const p = (cycle - 0.75) / 0.25;  // 0..1
    radius = DOTS_RADIUS * p;
  }
  
  // Вращение — 1 полный оборот за цикл
  const angleOffset = cycle * 360;
  
  for (let i = 0; i < 3; i++) {
    const angle = (i * 120 + angleOffset) * Math.PI / 180;
    const x = Math.cos(angle) * radius;
    const y = Math.sin(angle) * radius;
    const dot = document.getElementById('dot' + i);
    if (dot) {
      dot.style.transform = `translate(${x}px, ${y}px)`;
      // Прозрачность: в фазе схлопывания — ярче
      if (cycle > 0.5 && cycle < 0.75) {
        dot.style.opacity = '1';
        dot.style.boxShadow = '0 0 25px #3a8aff, 0 0 50px #3a8aff';
      } else {
        dot.style.opacity = '0.85';
        dot.style.boxShadow = '0 0 15px #3a8aff, 0 0 30px #3a8aff';
      }
    }
  }
  
  dotsAnimationId = requestAnimationFrame(animateDots);
}

function startDotsAnimation() {
  if (dotsAnimationId) return;
  dotsAnimationId = requestAnimationFrame(animateDots);
}

function stopDotsAnimation() {
  if (dotsAnimationId) {
    cancelAnimationFrame(dotsAnimationId);
    dotsAnimationId = null;
  }
}


// === THREE.JS 3D-МОДЕЛЬ ===
let scene, camera, renderer, controls;
let robot = {};  // группы суставов
let threeInitialized = false;

function initThree() {
  if (threeInitialized) return;
  const container = document.getElementById('threeCanvas');
  if (!container) {
    console.warn('[3D] контейнер не найден');
    return;
  }
  if (typeof THREE === 'undefined') {
    console.warn('[3D] Three.js не загружен');
    return;
  }

  // Сцена
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x000000);

  // Камера
  const w = container.clientWidth || window.innerWidth;
  const h = container.clientHeight || 400;
  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 1000);
  camera.position.set(4, 3, 6);
  camera.lookAt(0, 1, 0);

  // Рендер
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  container.appendChild(renderer.domElement);

  // Свет
  const ambient = new THREE.AmbientLight(0x3a8aff, 0.4);
  scene.add(ambient);

  const dir = new THREE.DirectionalLight(0x6a9aff, 1.2);
  dir.position.set(5, 10, 7);
  scene.add(dir);

  const fill = new THREE.DirectionalLight(0x3a8aff, 0.6);
  fill.position.set(-5, 3, -5);
  scene.add(fill);

  // === МОДЕЛЬ 6-DOF МАНИПУЛЯТОРА ===
  buildRobot();

  function buildRobot() {
    // Материалы — сохраняем текущий синий стиль
    const mat = new THREE.MeshStandardMaterial({
      color: 0x3a8aff,
      emissive: 0x1a3a6a,
      emissiveIntensity: 0.6,
      metalness: 0.8,
      roughness: 0.25,
    });
    const matDark = new THREE.MeshStandardMaterial({
      color: 0x1a2a4a,
      emissive: 0x0a1a3a,
      emissiveIntensity: 0.4,
      metalness: 0.9,
      roughness: 0.3,
    });
    const matJoint = new THREE.MeshStandardMaterial({
      color: 0x6a9aff,
      emissive: 0x2a5aaa,
      emissiveIntensity: 0.8,
      metalness: 0.9,
      roughness: 0.2,
    });

    // === БАЗА ===
    const baseGroup = new THREE.Group();
    baseGroup.position.y = 0;

    const baseCyl = new THREE.Mesh(
      new THREE.CylinderGeometry(0.55, 0.65, 0.25, 32),
      matDark
    );
    baseCyl.position.y = 0.125;
    baseGroup.add(baseCyl);

    const baseSphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.38, 24, 24),
      matJoint
    );
    baseSphere.position.y = 0.38;
    baseGroup.add(baseSphere);

    scene.add(baseGroup);
    robot.base = baseGroup;

    // === ПЛЕЧО (наклонная стойка) ===
    const shoulder = new THREE.Group();
    shoulder.position.y = 0.38;
    baseGroup.add(shoulder);
    robot.shoulder = shoulder;

    // Основной корпус плеча — вытянутый блок
    const shoulderBox = new THREE.Mesh(
      new THREE.BoxGeometry(0.35, 1.1, 0.35),
      mat
    );
    shoulderBox.position.y = 0.55;
    shoulder.add(shoulderBox);

    // Верхний сустав плеча
    const shoulderTop = new THREE.Mesh(
      new THREE.SphereGeometry(0.2, 20, 20),
      matJoint
    );
    shoulderTop.position.y = 1.1;
    shoulder.add(shoulderTop);

    // === ЛОКОТЬ ===
    const elbow = new THREE.Group();
    elbow.position.y = 1.1;
    shoulder.add(elbow);
    robot.elbow = elbow;

    const elbowBox = new THREE.Mesh(
      new THREE.BoxGeometry(0.3, 0.9, 0.3),
      mat
    );
    elbowBox.position.y = 0.45;
    elbow.add(elbowBox);

    // Сустав локтя
    const elbowSphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.18, 20, 20),
      matJoint
    );
    elbowSphere.position.y = 0.9;
    elbow.add(elbowSphere);

    // === ЗАПЯСТЬЕ PITCH ===
    const wristP = new THREE.Group();
    wristP.position.y = 0.9;
    elbow.add(wristP);
    robot.wristP = wristP;

    // Небольшой цилиндр-переходник
    const wristPCyl = new THREE.Mesh(
      new THREE.CylinderGeometry(0.14, 0.14, 0.25, 16),
      mat
    );
    wristPCyl.position.y = 0.125;
    wristP.add(wristPCyl);

    // === ЗАПЯСТЬЕ ROLL ===
    const wristR = new THREE.Group();
    wristR.position.y = 0.25;
    wristP.add(wristR);
    robot.wristR = wristR;

    const wristRSphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.15, 20, 20),
      matJoint
    );
    wristR.add(wristRSphere);

    // === СХВАТ (два пальца-губки) ===
    const gripper = new THREE.Group();
    gripper.position.y = 0.15;
    wristR.add(gripper);
    robot.gripper = gripper;

    // Ладонь — короткий блок
    const palm = new THREE.Mesh(
      new THREE.BoxGeometry(0.25, 0.1, 0.2),
      mat
    );
    palm.position.y = 0.05;
    gripper.add(palm);

    // Левый палец
    const fingerL = new THREE.Mesh(
      new THREE.BoxGeometry(0.07, 0.3, 0.15),
      mat
    );
    fingerL.position.set(-0.12, 0.25, 0);
    gripper.add(fingerL);

    // Правый палец
    const fingerR = new THREE.Mesh(
      new THREE.BoxGeometry(0.07, 0.3, 0.15),
      mat
    );
    fingerR.position.set(0.12, 0.25, 0);
    gripper.add(fingerR);

    robot.fingerL = fingerL;
    robot.fingerR = fingerR;
    robot.fingers = { left: fingerL, right: fingerR };

    console.log('[3D] модель построена');
  }

  // Решётка (пол)
  const grid = new THREE.GridHelper(10, 20, 0x3a8aff, 0x1a2a3a);
  grid.material.opacity = 0.3;
  grid.material.transparent = true;
  scene.add(grid);

  // OrbitControls (вращение)
  if (THREE.OrbitControls) {
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.enableZoom = true;
    controls.enableRotate = true;
    controls.minDistance = 3;
    controls.maxDistance = 15;
    controls.target.set(0, 1, 0);
    controls.update();
    console.log('[3D] OrbitControls подключён');
  } else {
    console.error('[3D] OrbitControls НЕ загружен!');
  }

  threeInitialized = true;
  
  // Тестовая поза — все в центр
  setJointAngles({
    base: 90,
    shoulder: 45,
    elbow: 135,
    wristP: 60,
    wristR: 90,
    gripper: 60,
  });
  
  animateThree();
  console.log('[3D] инициализация OK');
}

// === УСТАНОВКА УГЛОВ СУСТАВОВ ===
function setJointAngles(angles) {
  // === ОГРАНИЧЕНИЯ УГЛОВ (безопасные лимиты для сервоприводов) ===
  const LIMITS = {
    base:     { min: 0,   max: 180, def: 90 },
    shoulder: { min: 15,  max: 165, def: 90 },
    elbow:    { min: 30,  max: 150, def: 90 },
    wristP:   { min: 20,  max: 160, def: 90 },
    wristR:   { min: 0,   max: 180, def: 90 },
    gripper:  { min: 10,  max: 100, def: 30 }
  };

  function clamp(name, val) {
    if (val === undefined || val === null) return LIMITS[name].def;
    const L = LIMITS[name];
    return Math.max(L.min, Math.min(L.max, val));
  }

  if (!threeInitialized) return;

  // BASE — вращение вокруг Y (0..180)
  if (angles.base !== undefined && robot.base) {
    const a = clamp("base", angles.base);
    robot.base.rotation.y = (a - 90) * Math.PI / 180;
  }

  // SHOULDER — наклон вперед/назад (инвертируем знак, чтобы рука шла вперед)
  if (angles.shoulder !== undefined && robot.shoulder) {
    const a = clamp("shoulder", angles.shoulder);
    robot.shoulder.rotation.z = (a - 90) * Math.PI / 180;
  }

  // ELBOW — сгиб (инвертируем, чтобы рука сгибалась внутрь)
  if (angles.elbow !== undefined && robot.elbow) {
    const a = clamp("elbow", angles.elbow);
    robot.elbow.rotation.z = -(a - 90) * Math.PI / 180;
  }

  // WRIST PITCH — наклон кисти
  if (angles.wristP !== undefined && robot.wristP) {
    const a = clamp("wristP", angles.wristP);
    robot.wristP.rotation.z = -(a - 90) * Math.PI / 180;
  }

  // WRIST ROLL — поворот кисти
  if (angles.wristR !== undefined && robot.wristR) {
    const a = clamp("wristR", angles.wristR);
    robot.wristR.rotation.y = (a - 90) * Math.PI / 180;
  }

  // GRIPPER — раскрытие губок (0 = открыт, 180 = закрыт; у нас 10..100)
  if (angles.gripper !== undefined && robot.gripper) {
    const a = clamp("gripper", angles.gripper);
    const g = (a - 90) * Math.PI / 180;
    if (robot.fingers) {
      robot.fingers.left.position.x  = -0.12 - Math.sin(g) * 0.06;
      robot.fingers.right.position.x =  0.12 + Math.sin(g) * 0.06;
    }
  }

  // Сохраняем текущую позу в глобальную переменную (пригодится для ШИМ)
  if (!window.robotAngles) window.robotAngles = {};
  window.robotAngles = Object.assign({}, window.robotAngles, angles);
}

function animateThree() {
  if (!threeInitialized) return;
  requestAnimationFrame(animateThree);
  
  // Куб больше не крутится сам — OrbitControls рулит камерой
  if (controls) controls.update();
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

function resizeThree() {
  const container = document.getElementById('threeCanvas');
  if (!container || !renderer || !camera) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  if (w === 0 || h === 0) return;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}

window.addEventListener('resize', resizeThree);


// === КЛИК ВНЕ МЕНЮ ===
document.addEventListener('click', (e) => {
  const menu = document.getElementById('tabMenu');
  const burger = document.querySelector('.burger');
  const title = document.querySelector('.tab-title');
  if (!menu.contains(e.target) && !burger.contains(e.target) && !title.contains(e.target)) {
    menu.classList.remove('open');
  }
});


// ═══ СВЯЗКА СЛАЙДЕРОВ С 3D И ЯДРОМ ═══
function initManualControls() {
  const joints = ["base", "shoulder", "elbow", "wristP", "wristR", "gripper"];
  joints.forEach(function(j) {
    const sl = document.getElementById("sl-" + j);
    const val = document.getElementById("val-" + j);
    if (!sl) return;
    sl.addEventListener("input", function() {
      const a = parseInt(sl.value, 10);
      val.textContent = a;

      // 1) Мгновенно двигаем 3D
      const angles = {};
      angles[j] = a;
      if (typeof setJointAngles === "function") setJointAngles(angles);

      // 2) Отправляем в ядро
      fetch("/api/servo", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({joint: j.toLowerCase(), angle: a})
      }).catch(function(e){ console.warn("[SERVO] send fail", e); });
    });
  });

  // Кнопка HOME — сброс всех в центр
  const btnHome = document.getElementById("btn-home");
  if (btnHome) {
    btnHome.addEventListener("click", function() {
      const defs = {base:90, shoulder:90, elbow:90, wristP:90, wristR:90, gripper:30};
      Object.keys(defs).forEach(function(j) {
        const sl = document.getElementById("sl-" + j);
        const val = document.getElementById("val-" + j);
        if (sl) { sl.value = defs[j]; val.textContent = defs[j]; }
      });
      if (typeof setJointAngles === "function") setJointAngles(defs);
      fetch("/api/servo", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({joint: "home", angle: 90})
      }).catch(function(){});
    });
  }

  console.log("[GENESIS] Ручное управление подключено.");
}

// Вызываем после инициализации 3D
window.addEventListener("load", function() {
  setTimeout(function() {
    if (typeof initManualControls === "function") initManualControls();
  }, 800);
});


// Регистрация Service Worker (PWA)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/static/sw.js')
      .then(function(reg) { console.log('[PWA] SW зарегистрирован:', reg.scope); })
      .catch(function(err) { console.warn('[PWA] SW ошибка:', err); });
  });
}
</script>

<!-- === МОДАЛЬНОЕ ОКНО ИСТОРИИ === -->
<div id="historyModal" class="history-modal">
  <div class="history-box">
    <div class="history-header">
      <span>ИСТОРИЯ</span>
      <span class="history-close" onclick="closeHistory()">×</span>
    </div>
    <div class="history-pin" id="historyPin">
      <p>Введите PIN:</p>
      <input type="password" id="historyPinInput" maxlength="10" placeholder="····" autocomplete="off">
      <button class="history-btn" onclick="unlockHistory()">Открыть</button>
      <div class="history-err" id="historyErr"></div>
    </div>
    <div class="history-content" id="historyContent" style="display:none; flex-direction: column; flex: 1 1 0; min-height: 0;">
      <div class="history-list" id="historyList"></div>
      <button class="history-btn danger" onclick="clearHistory()">Очистить историю</button>
    </div>
  </div>
</div>

<style>
  .history-modal {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.85);
    z-index: 9999;
    align-items: center;
    justify-content: center;
  }
  .history-modal.active { display: flex; }
  .history-box {
    width: 92%;
    max-width: 500px;
    height: 80vh;
    max-height: 80vh;
    background: #0a0f1a;
    border: 1px solid #1a3a6a;
    border-radius: 14px;
    padding: 18px;
    color: #c8dcff;
    font-family: monospace;
    box-shadow: 0 0 40px rgba(58, 138, 255, 0.3);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .history-header {
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    letter-spacing: 3px;
    color: #6a9aff;
    margin-bottom: 14px;
  }
  .history-close {
    cursor: pointer;
    font-size: 22px;
    color: #6a9aff;
    line-height: 1;
  }
  .history-close:active { color: #fff; }
  .history-pin p { margin: 10px 0; }
  #historyPinInput {
    width: 100%;
    padding: 10px;
    background: #0d1524;
    border: 1px solid #1a3a6a;
    color: #c8dcff;
    font-family: monospace;
    border-radius: 8px;
    box-sizing: border-box;
    letter-spacing: 4px;
    text-align: center;
  }
  .history-btn {
    width: 100%;
    margin-top: 12px;
    padding: 10px;
    background: rgba(58, 138, 255, 0.15);
    border: 1px solid #3a8aff;
    color: #c8dcff;
    font-family: monospace;
    letter-spacing: 2px;
    border-radius: 8px;
    cursor: pointer;
  }
  .history-btn:active { background: rgba(58, 138, 255, 0.35); }
  .history-btn.danger {
    border-color: #8f2a2a;
    background: rgba(143, 42, 42, 0.15);
    color: #ff8888;
  }
  .history-btn.danger:active { background: rgba(143, 42, 42, 0.35); }
  .history-err {
    color: #ff6666;
    font-size: 12px;
    text-align: center;
    margin-top: 8px;
    min-height: 16px;
  }
  .history-list {
    flex: 1 1 0;
    min-height: 0;
    overflow-y: auto;
    padding-right: 6px;
    margin-bottom: 8px;
  }
  .history-list::-webkit-scrollbar { width: 6px; }
  .history-list::-webkit-scrollbar-thumb { background: #1a3a6a; border-radius: 3px; }
  .hist-item {
    padding: 8px 10px;
    margin: 6px 0;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.4;
    word-wrap: break-word;
  }
  .hist-item.user {
    background: rgba(58, 138, 255, 0.12);
    border-left: 3px solid #3a8aff;
  }
  .hist-item.assistant {
    background: rgba(143, 42, 42, 0.12);
    border-left: 3px solid #8f2a2a;
  }
  .hist-item .time {
    display: block;
    font-size: 10px;
    color: #5a7aaa;
    margin-top: 4px;
  }
</style>

<script>
// === ИСТОРИЯ ЧАТА ===
function showHistory() {
  document.getElementById('historyModal').classList.add('active');
  document.getElementById('historyPin').style.display = 'block';
  document.getElementById('historyContent').style.display = 'none';
  document.getElementById('historyErr').textContent = '';
  document.getElementById('historyPinInput').value = '';
  setTimeout(function() {
    document.getElementById('historyPinInput').focus();
  }, 100);
}

function closeHistory() {
  document.getElementById('historyModal').classList.remove('active');
}

function unlockHistory() {
  var pin = document.getElementById('historyPinInput').value;
  var err = document.getElementById('historyErr');
  err.textContent = '';
  fetch('/api/history', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pin: pin})
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (!data.ok) {
      err.textContent = 'Неверный PIN';
      document.getElementById('historyPinInput').value = '';
      return;
    }
    document.getElementById('historyPin').style.display = 'none';
    document.getElementById('historyContent').style.display = 'flex';
    renderHistory(data.history || []);
  })
  .catch(function(e) {
    err.textContent = 'Ошибка связи';
    console.warn('[HISTORY]', e);
  });
}

function renderHistory(items) {
  var list = document.getElementById('historyList');
  if (!items || !items.length) {
    list.innerHTML = '<div class="hist-item assistant">История пуста, Сэр.</div>';
    return;
  }
  var html = '';
  items.forEach(function(m) {
    var role = (m.role === 'user') ? 'user' : 'assistant';
    var time = (m.timestamp || '').replace('T', ' ').substring(0, 19);
    var text = (m.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html += '<div class="hist-item ' + role + '">' + text +
            '<span class="time">' + time + '</span></div>';
  });
  list.innerHTML = html;
  list.scrollTop = list.scrollHeight;
}

function clearHistory() {
  if (!confirm('Очистить всю историю, Сэр?')) return;
  var pin = document.getElementById('historyPinInput').value || window.GENESIS_PIN;
  // PIN мы уже не храним в поле после успешного входа — используем сохранённый
  // Проще: попросить заново. Здесь используем window.GENESIS_PIN (быстрый вариант).
  fetch('/api/history/clear', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pin: pin})
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.ok) {
      renderHistory([]);
    } else {
      alert('Не удалось очистить: неверный PIN');
    }
  })
  .catch(function(e) { console.warn('[HISTORY] clear', e); });
}
</script>
</body>
</html>
"""

# ============================================================
#  ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template_string(HTML, PIN=PIN_DEFAULT)

@app.route("/static/<path:filename>")
def serve_static(filename):
    from flask import send_from_directory
    import os
    return send_from_directory(os.path.expanduser("~/static"), filename)


@app.route("/api/history", methods=["POST"])
def api_history():
    """Возвращает историю чата после проверки PIN."""
    import json as _json, os as _os
    try:
        data = request.get_json(force=True, silent=True) or {}
        pin = str(data.get("pin", ""))
        if pin != PIN_DEFAULT:
            return jsonify({"ok": False, "error": "wrong_pin"}), 403

        mem_path = _os.path.expanduser("~/doom_memory.json")
        if not _os.path.exists(mem_path):
            return jsonify({"ok": True, "history": [], "total": 0})

        with open(mem_path, "r", encoding="utf-8") as f:
            mem = _json.load(f)

        conv = mem.get("conversation", [])
        return jsonify({"ok": True, "history": conv, "total": len(conv)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/history/clear", methods=["POST"])
def api_history_clear():
    """Очищает историю чата (после проверки PIN)."""
    import json as _json, os as _os
    try:
        data = request.get_json(force=True, silent=True) or {}
        pin = str(data.get("pin", ""))
        if pin != PIN_DEFAULT:
            return jsonify({"ok": False, "error": "wrong_pin"}), 403

        mem_path = _os.path.expanduser("~/doom_memory.json")
        if _os.path.exists(mem_path):
            with open(mem_path, "r", encoding="utf-8") as f:
                mem = _json.load(f)
        else:
            mem = {}

        mem["conversation"] = []
        with open(mem_path, "w", encoding="utf-8") as f:
            _json.dump(mem, f, ensure_ascii=False, indent=2)

        # Сброс памяти в ядре, если есть
        try:
            if GLOBAL_CORE is not None and hasattr(GLOBAL_CORE, "long_mem"):
                GLOBAL_CORE.long_mem.conversation = []
                GLOBAL_CORE.long_mem.save()
        except Exception:
            pass

        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/last_pose", methods=["GET"])
def api_last_pose():
    """Возвращает последнюю позу робота (углы суставов)."""
    try:
        if GLOBAL_CORE is None:
            return jsonify({"ok": False, "pose": {}})
        pose = getattr(GLOBAL_CORE, "last_pose", {}) or {}
        return jsonify({"ok": True, "pose": pose})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"response": "..."})
    
    if GLOBAL_CORE is None:
        return jsonify({"response": "Сэр, ядро не подключено."})
    
    try:
        # 1. Получаем ответ от ядра
        response = GLOBAL_CORE.ask(text)
        if not response:
            response = "..."
        
        # 2. Генерируем TTS для ОТВЕТА
        audio_url = None
        if GLOBAL_CORE.tts and response:
            import re as _re
            import subprocess
            
            clean = _re.sub(r'[*_`#>]', '', response)
            clean = _re.sub(r'[;"\'`$&|\\<>]', '', clean)
            clean = _re.sub(r'\s+', ' ', clean).strip()
            if len(clean) > 400:
                clean = clean[:400] + "..."
            
            cache_path = GLOBAL_CORE.tts._cache_path(clean)
            
            # Если нет в кэше — генерируем
            if not os.path.exists(cache_path):
                raw = os.path.join(os.path.expanduser("~/doom_tts_cache"), "_raw_web.mp3")
                try:
                    subprocess.run([
                        "edge-tts", "--voice", GLOBAL_CORE.tts.voice,
                        "--text", clean, "--write-media", raw
                    ], timeout=20, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run([
                        "ffmpeg", "-y", "-i", raw,
                        "-af", "asetrate=24000*0.88,aresample=24000,aecho=0.8:0.88:20:0.4",
                        cache_path
                    ], timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as _e:
                    print(f"[WEB TTS] ошибка: {_e}")
            
            if os.path.exists(cache_path):
                audio_url = f"/audio/{os.path.basename(cache_path)}"
        
        return jsonify({
            "response": response,
            "audio_url": audio_url
        })
    except Exception as e:
        return jsonify({"response": f"Сэр, ошибка: {e}"})


@app.route("/api/servo", methods=["POST"])
def api_servo():
    """Приём углов от слайдеров. Передаёт в ядро через dispatcher."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        joint = str(data.get("joint", "")).lower()
        try:
            angle = int(data.get("angle", 90))
        except Exception:
            angle = 90

        # Лимиты (должны совпадать с JS LIMITS)
        LIMITS = {
            "base":     (0, 180),
            "shoulder": (15, 165),
            "elbow":    (30, 150),
            "wristp":   (20, 160),
            "wristr":   (0, 180),
            "gripper":  (10, 100),
        }
        if joint not in LIMITS:
            return jsonify({"ok": False, "error": "unknown joint"}), 400

        lo, hi = LIMITS[joint]
        angle = max(lo, min(hi, angle))

        # Отправка в ядро (сейчас заглушка — dispatcher=None)
        try:
            import json as _json
            action = _json.dumps({"action": "servo", "joint": joint, "angle": angle})
            if core is not None:
                core._execute_action(action)
            print(f"[SERVO] {joint} = {angle}")
        except Exception as e:
            print(f"[SERVO] error: {e}")

        return jsonify({"ok": True, "joint": joint, "angle": angle})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/audio/<filename>")
def serve_audio(filename):
    from flask import send_from_directory
    return send_from_directory(os.path.expanduser("~/doom_tts_cache"), filename)

# ============================================================
#  ЗАПУСК
# ============================================================

def run_web(core=None, bridge=None, host="0.0.0.0", port=5000):
    global GLOBAL_CORE, GLOBAL_BRIDGE
    GLOBAL_CORE = core
    GLOBAL_BRIDGE = bridge
    print(f"[GENESIS WEB] Запуск на http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    # Тестовый запуск — без ядра
    run_web()
