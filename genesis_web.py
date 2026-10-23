"""
genesis_web.py — Веб-интерфейс KAIROS.
Gemini-стиль, 2 вкладки, анимации, защита.
"""

from flask import Flask, render_template_string, request, jsonify
import os

app = Flask(__name__)


# ============================================================
#  НАСТРОЙКИ
# ============================================================

# PIN читается из ~/.genesis_pin (создаётся вручную или через настройки)
def _load_secret(key_name):
    """Читает значение из ~/.genesis_secrets по имени ключа."""
    import os as _os
    path = _os.path.expanduser("~/.genesis_secrets")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(key_name + "="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


def _load_pin():
    import os
    path = os.path.expanduser("~/.genesis_pin")
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1234"

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
:root {
  --bg-main: #000000;
  --bg-card: #1a1a1a;
  --accent: #3a8aff;
  --text: #e0e0e0;
  --star: #3a8aff;
}

  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    width: 100%; height: 100%;
    background: var(--bg-main);
    color: var(--text);
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
    background: var(--bg-main);
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
    color: var(--text);
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
    color: var(--text);
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
    background: var(--bg-card);
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
  .tab-item:hover { background: rgba(58, 138, 255, 0.15); }
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
    width: 120px; height: 120px;
    display: flex; align-items: center; justify-content: center;
    transition: opacity 0.5s, transform 0.5s;
    position: absolute;
    top: 42%;
    left: 50%;
    transform: translate(-50%, -50%);
  }
  .star-container.hidden {
    opacity: 0;
    pointer-events: none;
    transform: translate(-50%, -50%) scale(0.5);
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
    from { transform: translate(-50%, -50%) rotate(0deg); }
    to { transform: translate(-50%, -50%) rotate(180deg); }
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
    background: var(--accent);
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
    color: var(--text);
    line-height: 1.3;
    transition: opacity 0.5s, transform 0.5s;
    word-wrap: break-word;
  }
  .message.hidden {
    opacity: 0;
    transform: translateY(-20px);
    pointer-events: none;
  }

  /* === ЧАТ (пузыри) === */
  .chat-messages {
    position: absolute;
    top: 60px;
    bottom: 100px;
    left: 0;
    right: 0;
    overflow-y: auto;
    padding: 10px 16px;
    display: none;
    flex-direction: column;
    gap: 10px;
    scroll-behavior: smooth;
  }
  .chat-messages.active { display: flex; }

  /* === ВКЛАДКА ИНФО === */
  .info-view {
    position: absolute;
    top: 60px;
    bottom: 100px;
    left: 0;
    right: 0;
    overflow-y: auto;
    padding: 12px 14px;
    display: none;
    flex-direction: column;
    gap: 12px;
  }
  .info-view.active { display: flex; }

  /* === ВКЛАДКА ЗАМЕТКИ === */
  .notes-view {
    position: absolute;
    top: 60px;
    bottom: 100px;
    left: 0;
    right: 0;
    overflow-y: auto;
    padding: 12px 14px;
    display: none;
    flex-direction: column;
    gap: 12px;
  }
  .notes-view.active { display: flex; }

  /* === ВКЛАДКА НАСТРОЙКИ === */
  .settings-view {
    position: absolute;
    top: 60px;
    bottom: 100px;
    left: 0;
    right: 0;
    overflow-y: auto;
    padding: 12px 14px;
    display: none;
    flex-direction: column;
    gap: 12px;
  }
  .settings-view.active { display: flex; }
  .settings-card {
    background: var(--bg-card);
    border: 1px solid #1a3a6a;
    border-radius: 14px;
    padding: 14px 16px;
    color: #c8dcff;
  }
  .settings-title {
    font-size: 13px;
    letter-spacing: 2px;
    color: #6a9aff;
    margin-bottom: 10px;
  }
  .settings-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .settings-btn {
    padding: 8px 14px;
    background: var(--bg-card);
    border: 1px solid #1a3a6a;
    border-radius: 8px;
    color: #8aa8d0;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .settings-btn.active {
    background: var(--accent);
    color: #c8dcff;
    border-color: #3a8aff;
  }
  .settings-note {
    font-size: 12px;
    color: #5a7aaa;
    margin-top: 8px;
  }

  .notes-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 4px;
  }
  .notes-tab {
    flex: 1;
    padding: 10px 8px;
    background: var(--bg-card);
    border: 1px solid #1a3a6a;
    border-radius: 10px;
    text-align: center;
    font-size: 13px;
    color: #8aa8d0;
    cursor: pointer;
    transition: all 0.2s;
  }
  .notes-tab.active {
    background: var(--accent);
    color: #c8dcff;
    border-color: #3a8aff;
  }
  .notes-content {
    flex: 1;
    display: none;
    flex-direction: column;
    gap: 10px;
  }
  .notes-content.active { display: flex; }
  .notes-empty {
    background: var(--bg-card);
    border: 1px dashed #1a3a6a;
    border-radius: 14px;
    padding: 30px 20px;
    text-align: center;
    color: #6a9aff;
    font-size: 15px;
  }
  .info-card {
    background: var(--bg-card);
    border: 1px solid #1a3a6a;
    border-radius: 14px;
    padding: 14px 16px;
    color: #c8dcff;
  }
  .info-card-title {
    font-size: 13px;
    letter-spacing: 2px;
    color: #6a9aff;
    margin-bottom: 10px;
  }
  .info-card-body { font-size: 15px; line-height: 1.5; }
  .weather-row { display: flex; align-items: center; gap: 14px; }
  .weather-icon { font-size: 42px; }
  .weather-temp { font-size: 26px; font-weight: 600; }
  .weather-desc { font-size: 13px; color: #8aa8d0; }
  .space-split { display: flex; gap: 14px; }
  .space-half { flex: 1; }
  .moon-icon { font-size: 38px; display: block; text-align: center; }
  .moon-name { text-align: center; font-size: 12px; color: #8aa8d0; margin-top: 4px; }
  .currencies {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px; text-align: center;
  }
  .currency-item { display: flex; flex-direction: column; gap: 4px; }
  .currency-icon { font-size: 22px; }
  .currency-code { font-size: 11px; color: #6a9aff; }
  .currency-value { font-size: 14px; font-weight: 600; }
  .news-item {
    padding: 10px 0;
    border-bottom: 1px solid #1a2a4a;
    font-size: 16px;
    font-weight: 500;
    line-height: 1.5;
    color: #c8dcff;
    text-decoration: none;
    display: block;
    transition: background 0.2s;
  }
  a.news-item:hover { background: #0f1a2e; }
  a.news-item:last-child { border-bottom: none; }
  .news-item:last-child { border-bottom: none; }
  .news-tag { color: #6a9aff; font-size: 13px; font-weight: 600; }
  .chat-msg {
    max-width: 85%;
    padding: 12px 16px;
    border-radius: 16px;
    font-size: 17px;
    font-weight: 500;
    line-height: 1.5;
    word-wrap: break-word;
    animation: msgIn 0.25s ease-out;
  }
  @keyframes msgIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .chat-msg.user {
    align-self: flex-end;
    background: linear-gradient(135deg, #3a8aff, #6a4aff);
    color: #fff;
    border-bottom-right-radius: 4px;
  }
  .chat-msg.kairos {
    align-self: flex-start;
    background: #131a2c;
    color: #d6e4ff;
    border: 1px solid #1a2a4a;
    border-bottom-left-radius: 4px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }
  .chat-msg.kairos .mini-star {
    width: 22px; height: 22px;
    flex-shrink: 0;
    margin-top: 2px;
    filter: drop-shadow(0 0 6px #3a8aff);
  }
  .chat-msg.kairos .msg-text { flex: 1; }
  .chat-msg .msg-time {
    display: block;
    font-size: 11px;
    opacity: 0.5;
    margin-top: 4px;
  }
  .chat-typing {
    align-self: flex-start;
    background: #131a2c;
    border: 1px solid #1a2a4a;
    padding: 12px 16px;
    border-radius: 16px;
    border-bottom-left-radius: 4px;
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .chat-typing .t-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    animation: typingBlink 1.2s infinite;
  }
  .chat-typing .t-dot:nth-child(2) { animation-delay: 0.2s; }
  .chat-typing .t-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes typingBlink {
    0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
    30% { opacity: 1; transform: translateY(-3px); }
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
    background: var(--accent);
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
    background: var(--bg-card);
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
    color: var(--text);
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
    background: var(--bg-main);
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
    background: var(--bg-card);
    border: 1px solid #3a3a3a;
    border-radius: 12px;
    padding: 14px 20px;
    color: var(--text);
    font-size: 20px;
    text-align: center;
    letter-spacing: 8px;
    width: 200px;
    font-family: monospace;
  }
  .pin-btn {
    background: var(--accent);
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


.ctx-sources {
  display: block;
  font-size: 11px;
  color: #6a7b8c;
  margin-top: 4px;
  letter-spacing: 0.3px;
  font-style: italic;
}

.ctx-image {
  display: block;
  max-width: 240px;
  max-height: 180px;
  margin-top: 8px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid rgba(106, 123, 140, 0.25);
}

/* ==================== ЗАМЕТКИ ==================== */
.notes-view {
  padding: 12px 14px;
}
.notes-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}
.notes-tab {
  flex: 1;
  text-align: center;
  padding: 10px 6px;
  border-radius: 10px;
  background: rgba(106, 123, 140, 0.1);
  color: #8b98a8;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  user-select: none;
}
.notes-tab.active {
  background: var(--accent);
  color: #fff;
}
.notes-content {
  display: none;
}
.notes-content.active {
  display: block;
}
.notes-input-row {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}
.notes-input {
  flex: 1;
  min-width: 0;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid rgba(106, 123, 140, 0.25);
  background: rgba(30, 36, 46, 0.9);
  color: #e6eaf0;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}
.notes-input::placeholder {
  color: #6a7b8c;
}
.notes-input:focus {
  border-color: #3a8aff;
  background: rgba(30, 36, 46, 1);
}
.notes-when {
  flex: 0 0 110px;
  font-size: 12px;
}
.notes-btn {
  flex: 0 0 44px;
  padding: 12px 0;
  border-radius: 10px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}
.notes-btn:hover {
  background: #2a7aef;
}
.notes-btn:active {
  background: #1a6adf;
}
.notes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.notes-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(58, 138, 255, 0.08);
  border-left: 3px solid #3a8aff;
  color: #d8dde5;
  font-size: 14px;
  line-height: 1.4;
  word-break: break-word;
}
.notes-item-text {
  flex: 1;
  min-width: 0;
}
.notes-item-meta {
  display: block;
  font-size: 11px;
  color: #6a7b8c;
  margin-top: 4px;
}
.notes-item-del {
  flex: 0 0 auto;
  background: transparent;
  border: none;
  color: #ff5a5a;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.notes-empty {
  text-align: center;
  color: #6a7b8c;
  font-size: 13px;
  font-style: italic;
  padding: 20px;
}

.ctx-link {
  display: inline-block;
  margin-top: 6px;
  margin-left: 6px;
  font-size: 12px;
  color: #5a9fd4;
  text-decoration: none;
  font-style: italic;
  letter-spacing: 0.3px;
  transition: color 0.2s;
}
.ctx-link:hover {
  color: #8bc0e8;
  text-decoration: underline;
}


.settings-color-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
  color: var(--text);
}
.settings-color-row label { color: #8b98a8; }
.settings-color-row input[type="color"] {
  width: 60px;
  height: 32px;
  border: 1px solid rgba(106, 123, 140, 0.3);
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
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
        <span id="tabTitle">💬 Основное</span>
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
          <span>💬 Основное</span>
          <span class="check">✓</span>
        </div>
        <div class="tab-item" onclick="switchTab(1)" id="tabItem1">
          <span>🦾 Управление</span>
          <span class="check" style="display:none">✓</span>
        </div>
        <div class="tab-item" onclick="switchTab(2)" id="tabItem2">
          <span>📰 Инфо</span>
          <span class="check" style="display:none">✓</span>
        </div>
        <div class="tab-item" onclick="switchTab(3)" id="tabItem3">
          <span>📝 Заметки</span>
          <span class="check" style="display:none">✓</span>
        </div>
        <div class="tab-item" onclick="switchTab(4)" id="tabItem4">
          <span>⚙️ Настройки</span>
          <span class="check" style="display:none">✓</span>
        </div>
      </div>

  <!-- ВКЛАДКА 1 — ОСНОВНОЕ -->
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

      <div class="main" id="mainView">
    <div class="chat-messages" id="chatMessages"></div>
    
    <div class="dots-container" id="dotsContainer">
      <div class="dot" id="dot0"></div>
      <div class="dot" id="dot1"></div>
      <div class="dot" id="dot2"></div>
    </div>
    <div class="message" id="message">Сэр, системы готовы</div>
    <div class="mic-wave" id="micWave">
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
      <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
    </div>
  </div>

  <!-- ВКЛАДКА ИНФО -->
  <div class="info-view" id="infoView">

      <div class="info-card">
        <div class="info-card-title">🌤 ПОГОДА</div>
        <div class="weather-row">
          <div class="weather-icon" id="weatherIcon">☀️</div>
          <div>
            <div class="weather-temp" id="weatherTemp">—°C</div>
            <div class="weather-desc" id="weatherDesc">Гродно · загрузка...</div>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="info-card-title">🔭 КОСМОС</div>
        <div class="space-split">
          <div class="space-half">
            <span class="moon-icon" id="moonIcon">🌕</span>
            <div class="moon-name" id="moonName">Полнолуние</div>
          </div>
          <div class="space-half" id="spaceFact">
            🪐 Юпитер в 318 раз тяжелее Земли.
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="info-card-title">💱 КУРСЫ ВАЛЮТ</div>
        <div class="currencies">
          <div class="currency-item">
            <span class="currency-icon">💰</span>
            <span class="currency-code">PLN</span>
            <span class="currency-value" id="curPLN">—</span>
          </div>
          <div class="currency-item">
            <span class="currency-icon">💵</span>
            <span class="currency-code">USD</span>
            <span class="currency-value" id="curUSD">—</span>
          </div>
          <div class="currency-item">
            <span class="currency-icon">💶</span>
            <span class="currency-code">EUR</span>
            <span class="currency-value" id="curEUR">—</span>
          </div>
          <div class="currency-item">
            <span class="currency-icon">🪙</span>
            <span class="currency-code">BYN</span>
            <span class="currency-value" id="curBYN">1.00</span>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="info-card-title">🌐 НОВОСТИ</div>
        <div class="info-card-body" id="newsList">
          <div class="news-item"><span class="news-tag">🦏 Животные:</span> В Африке осталось мало носорогов...</div>
          <div class="news-item"><span class="news-tag">🛰️ Технологии:</span> SpaceX готовит новый запуск...</div>
          <div class="news-item"><span class="news-tag">⚽ Спорт:</span> Матч Барселона — Реал перенесён...</div>
        </div>
      </div>

    </div>

  <!-- ВКЛАДКА НАСТРОЙКИ -->
    <div class="settings-view" id="settingsView">

      <div class="settings-card">
        <div class="settings-title">🌍 ЯЗЫК</div>
        <div class="settings-row">
          <button class="settings-btn active" onclick="setLang('ru')">🇷🇺 Русский</button>
          <button class="settings-btn" onclick="setLang('en')">🇬🇧 English</button>
          <button class="settings-btn" onclick="setLang('pl')">🇵🇱 Polski</button>
        </div>
        <div class="settings-note">Перевод интерфейса — в разработке.</div>
      </div>

      <div class="settings-card">
        <div class="settings-title">🎨 ТЕМА (ЦВЕТА)</div>
        <div class="settings-color-row">
          <label>Фон:</label>
          <input type="color" id="themeBg" value="#000000" onchange="applyTheme()">
        </div>
        <div class="settings-color-row">
          <label>Акцент:</label>
          <input type="color" id="themeAccent" value="#3a8aff" onchange="applyTheme()">
        </div>
        <div class="settings-color-row">
          <label>Звезда:</label>
          <input type="color" id="themeStar" value="#3a8aff" onchange="applyTheme()">
        </div>
        <div class="settings-row" style="margin-top:10px;">
          <button class="settings-btn" onclick="resetTheme()">↺ Сбросить</button>
        </div>
      </div>

      <div class="settings-card">
        <div class="settings-title">🔊 ЗВУК</div>
        <div class="settings-row">
          <button class="settings-btn">🔊 Вкл</button>
          <button class="settings-btn">🔇 Выкл</button>
        </div>
      </div>

      <div class="settings-card">
        <div class="settings-title">🔐 БЕЗОПАСНОСТЬ</div>
        <div class="settings-row">
          <button class="settings-btn" onclick="changePin()">Сменить PIN</button>
        </div>
      </div>

      <div class="settings-card">
        <div class="settings-title">🖥️ ИНТЕРФЕЙС</div>
        <div class="settings-row">
          <button class="settings-btn">Шрифт меньше</button>
          <button class="settings-btn">Шрифт больше</button>
        </div>
      </div>

      <div class="settings-card">
        <div class="settings-title">📊 СИСТЕМА</div>
        <div class="settings-note">
          GENESIS v0.1 · KAIROS<br>
          Все системы в норме, Сэр.
        </div>
      </div>

    </div>

    <!-- ВКЛАДКА ЗАМЕТКИ -->
    <div class="notes-view" id="notesView">

      <div class="notes-tabs">
        <div class="notes-tab active" id="notesTab0" onclick="switchNotesTab(0)">📋 Заметки</div>
        <div class="notes-tab" id="notesTab1" onclick="switchNotesTab(1)">⏰ Напоминания</div>
        <div class="notes-tab" id="notesTab2" onclick="switchNotesTab(2)">📙 Дневник</div>
      </div>

      <div class="notes-content active" id="notesContent0">
        <div class="notes-input-row">
          <input type="text" class="notes-input" id="noteInput0" placeholder="Новая заметка...">
          <button class="notes-btn" onclick="addNote(0)">+</button>
        </div>
        <div class="notes-list" id="notesList0"></div>
        <div class="notes-empty" id="notesEmpty0">📋 Здесь будут ваши заметки, Сэр.</div>
      </div>

      <div class="notes-content" id="notesContent1">
        <div class="notes-input-row">
          <input type="text" class="notes-input" id="noteInput1" placeholder="Текст напоминания...">
          <input type="text" class="notes-input notes-when" id="noteWhen1" placeholder="Когда (2026-10-17 09:00)">
          <button class="notes-btn" onclick="addNote(1)">+</button>
        </div>
        <div class="notes-list" id="notesList1"></div>
        <div class="notes-empty" id="notesEmpty1">⏰ Напоминания появятся здесь.</div>
      </div>

      <div class="notes-content" id="notesContent2">
        <div class="notes-input-row">
          <input type="text" class="notes-input" id="noteInput2" placeholder="Запись в дневник...">
          <button class="notes-btn" onclick="addNote(2)">+</button>
        </div>
        <div class="notes-list" id="notesList2"></div>
        <div class="notes-empty" id="notesEmpty2">📙 Дневник: записи по датам.</div>
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
          background: var(--accent);
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

function setLang(lang) {
    console.log('[SETTINGS] Язык:', lang);
    // Пока — только логируем. Реализация — позже.
  }

  function changePin() {
    var newPin = prompt('Новый PIN:', '');
    if (newPin && newPin.length > 0) {
      fetch('/api/change_pin', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({pin: newPin})
      }).then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.ok) alert('PIN изменён, Сэр.');
          else alert('Ошибка: ' + (d.error || 'не удалось'));
        })
        .catch(function() { alert('Ошибка сети.'); });
    }
  }

  function switchNotesTab(idx) {
    var i;
    for (i = 0; i < 3; i++) {
      var tab = document.getElementById('notesTab' + i);
      var content = document.getElementById('notesContent' + i);
      if (i === idx) {
        if (tab) tab.classList.add('active');
        if (content) content.classList.add('active');
      } else {
        if (tab) tab.classList.remove('active');
        if (content) content.classList.remove('active');
      }
    }
  }

  function loadNews() {
    fetch('/api/news')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.ok) { console.warn('[NEWS]', d.error); return; }
        var list = document.getElementById('newsList');
        if (!list) return;
        var html = '';
        var i;
        for (i = 0; i < d.news.length; i++) {
          var n = d.news[i];
          var safeTitle = n.title.replace(/</g, '&lt;').replace(/>/g, '&gt;');
          html += '<a class="news-item" href="' + n.link + '" target="_blank" rel="noopener">' +
                    '<span class="news-tag">' + n.emoji + ' ' + n.tag + ':</span> ' +
                    safeTitle +
                  '</a>';
        }
        list.innerHTML = html;
      })
      .catch(function(e) { console.warn('[NEWS]', e); });
  }

  function loadSpace() {
    fetch('/api/space')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.ok) { console.warn('[SPACE]', d.error); return; }
        var mi = document.getElementById('moonIcon');
        var mn = document.getElementById('moonName');
        var sf = document.getElementById('spaceFact');
        if (mi) mi.textContent = d.moon_emoji;
        if (mn) mn.textContent = d.moon_name;
        if (sf) sf.textContent = '🪐 ' + d.fact;
      })
      .catch(function(e) { console.warn('[SPACE]', e); });
  }

  function loadCurrencies() {
    fetch('/api/currencies')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.ok) { console.warn('[CUR]', d.error); return; }
        var pln = document.getElementById('curPLN');
        var usd = document.getElementById('curUSD');
        var eur = document.getElementById('curEUR');
        var byn = document.getElementById('curBYN');
        if (pln) pln.textContent = d.PLN.toFixed(3);
        if (usd) usd.textContent = d.USD.toFixed(3);
        if (eur) eur.textContent = d.EUR.toFixed(3);
        if (byn) byn.textContent = '1.00';
      })
      .catch(function(e) { console.warn('[CUR]', e); });
  }

  function loadWeather() {
    fetch('/api/weather')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.ok) { console.warn('[WEATHER]', d.error); return; }
        var ic = document.getElementById('weatherIcon');
        var tp = document.getElementById('weatherTemp');
        var ds = document.getElementById('weatherDesc');
        if (ic) ic.textContent = d.emoji;
        if (tp) tp.textContent = d.temp + '°C';
        if (ds) ds.textContent = d.city + ' · ' + d.desc + ' · влажность ' + d.humidity + '%';
      })
      .catch(function(e) { console.warn('[WEATHER]', e); });
  }

  function switchTab(idx) {
    if (state.defense) return;
    state.tab = idx;
    document.getElementById('tabMenu').classList.remove('open');

    var main = document.getElementById('mainView');
    var manual = document.getElementById('manualView');
    var info = document.getElementById('infoView');
    var notes = document.getElementById('notesView');
    var settings = document.getElementById('settingsView');
    var title = document.getElementById('tabTitle');

    // Скрыть ВСЁ
    if (main) main.style.display = 'none';
    if (manual) manual.classList.remove('active');
    if (info) info.classList.remove('active');
    if (notes) notes.classList.remove('active');
    if (settings) settings.classList.remove('active');

    // Показать нужное
    if (idx === 0) {
      if (main) main.style.display = 'flex';
      if (title) title.textContent = '💬 Основное';
    } else if (idx === 1) {
      if (manual) manual.classList.add('active');
      if (title) title.textContent = '🦾 Управление';
      setTimeout(function() {
        if (typeof initThree === 'function') initThree();
        if (typeof resizeThree === 'function') resizeThree();
      }, 100);
    } else if (idx === 2) {
      if (info) info.classList.add('active');
      if (title) title.textContent = '📰 Инфо';
      if (typeof loadWeather === 'function') loadWeather();
      if (typeof loadCurrencies === 'function') loadCurrencies();
      if (typeof loadSpace === 'function') loadSpace();
      if (typeof loadNews === 'function') loadNews();
    } else if (idx === 3) {
      if (notes) notes.classList.add('active');
      if (title) title.textContent = '📝 Заметки';
    } else if (idx === 4) {
      if (settings) settings.classList.add('active');
      if (title) title.textContent = '⚙️ Настройки';
    }

    // Галочки в меню
    var k;
    for (k = 0; k < 5; k++) {
      var item = document.getElementById('tabItem' + k);
      if (!item) continue;
      var check = item.querySelector('.check');
      if (k === idx) {
        item.classList.add('active');
        if (check) check.style.display = 'inline';
      } else {
        item.classList.remove('active');
        if (check) check.style.display = 'none';
      }
    }
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

    // 1) Очистить пузыри
    var chat = document.getElementById('chatMessages');
    if (chat) {
      chat.innerHTML = '';
      chat.classList.remove('active');
    }

    // 2) Показать welcome
    var star = document.getElementById('starContainer');
    var msg = document.getElementById('message');
    if (star) star.classList.remove('hidden');
    if (msg) {
      msg.textContent = 'Сэр, системы готовы';
      msg.classList.remove('hidden');
    }

    // 3) Сбросить состояние "думает"
    state.thinking = false;

    // 4) Скрыть микрофонную волну
    var wave = document.getElementById('micWave');
    if (wave) wave.classList.remove('active');

    // 5) Лог
    console.log('[NEW CHAT] очищено.');
  }

function toggleSound() {
    state.soundOn = !state.soundOn;
    var btn = document.getElementById('soundBtn');
    if (!btn) return;
    if (state.soundOn) {
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>';
    } else {
      btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>';
    }
  }

  function toggleDefense() {
    if (state.defense) {
      document.getElementById('defenseLock').classList.add('active');
      document.getElementById('pinInput').focus();
    } else {
      state.defense = true;
      document.getElementById('app').classList.add('defense-mode');

      var main = document.getElementById('mainView');
      var manual = document.getElementById('manualView');
      var info = document.getElementById('infoView');
      var notes = document.getElementById('notesView');
      var settings = document.getElementById('settingsView');
      if (main) main.style.display = 'none';
      if (manual) manual.classList.remove('active');
      if (info) info.classList.remove('active');
      if (notes) notes.classList.remove('active');
      if (settings) settings.classList.remove('active');

      var star = document.getElementById('starContainer');
      if (star) {
        star.classList.remove('hidden');
        star.classList.add('defense');
        setTimeout(function() { star.classList.add('pulsing'); }, 1000);
      }

      var wave = document.getElementById('micWave');
      if (wave) wave.classList.remove('active');
      var chat = document.getElementById('chatMessages');
      if (chat) chat.classList.remove('active');
      hideMessage();
    }
  }

  function unlockDefense() {
    const pin = document.getElementById('pinInput').value;
    if (pin === window.GENESIS_PIN) {
      state.defense = false;
      document.getElementById('defenseLock').classList.remove('active');
      document.getElementById('app').classList.remove('defense-mode');

      // Убрать защиту со звезды
      var star = document.getElementById('starContainer');
      if (star) {
        star.classList.remove('pulsing');
        star.classList.remove('defense');
      }

      document.getElementById('pinInput').value = '';

      // Вернуть активную вкладку
      var activeTab = state.tab || 0;
      switchTab(activeTab);

      // Если чат пуст — показать welcome
      var chat = document.getElementById('chatMessages');
      var hasMessages = chat && chat.children.length > 0;
      if (!hasMessages && activeTab === 0) {
        if (star) star.classList.remove('hidden');
        setMessage('Сэр, системы готовы');
      }
    } else {
      document.getElementById('pinInput').value = '';
      document.getElementById('pinInput').placeholder = 'Неверно';
      setTimeout(function() {
        document.getElementById('pinInput').placeholder = '····';
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
// === ФУНКЦИИ ЧАТА ===
function _nowTime() {
  var d = new Date();
  return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
}
function _hideWelcome() {
  var sc = document.getElementById('starContainer');
  var dc = document.getElementById('dotsContainer');
  var mg = document.getElementById('message');
  if (sc) sc.classList.add('hidden');
  if (dc) dc.classList.remove('active');
  if (mg) mg.classList.add('hidden');
  var chat = document.getElementById('chatMessages');
  if (chat) chat.classList.add('active');
}
function _scrollChatBottom() {
  var chat = document.getElementById('chatMessages');
  if (chat) chat.scrollTop = chat.scrollHeight;
}
function addUserMessage(text) {
  _hideWelcome();
  var chat = document.getElementById('chatMessages');
  if (!chat) return;
  var div = document.createElement('div');
  div.className = 'chat-msg user';
  div.innerHTML = '<div>' + text.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div>' +
                  '<span class="msg-time">' + _nowTime() + '</span>';
  chat.appendChild(div);
  _scrollChatBottom();
}
function addKairosMessage(text) {
  _hideWelcome();
  var chat = document.getElementById('chatMessages');
  if (!chat) return;
  var div = document.createElement('div');
  div.className = 'chat-msg kairos';
  div.innerHTML = '<svg class="mini-star" viewBox="0 0 100 100">' +
      '<defs><linearGradient id="miniGrad" x1="0%" y1="0%" x2="100%" y2="100%">' +
        '<stop offset="0%" stop-color="#ff3a3a"/>' +
        '<stop offset="50%" stop-color="#6a4aff"/>' +
        '<stop offset="100%" stop-color="#3a8aff"/>' +
      '</linearGradient></defs>' +
      '<path d="M50 5 Q55 45 95 50 Q55 55 50 95 Q45 55 5 50 Q45 45 50 5 Z" fill="url(#miniGrad)"/>' +
    '</svg>' +
    '<div class="msg-text">' + text.replace(/</g,'&lt;').replace(/>/g,'&gt;') +
      '<span class="msg-time">' + _nowTime() + '</span>' +
    '</div>';
  chat.appendChild(div);
  _scrollChatBottom();
}
function showTypingBubble() {
  _hideWelcome();
  var chat = document.getElementById('chatMessages');
  if (!chat) return;
  var div = document.createElement('div');
  div.className = 'chat-typing';
  div.id = 'typingBubble';
  div.innerHTML = '<div class="t-dot"></div><div class="t-dot"></div><div class="t-dot"></div>';
  chat.appendChild(div);
  _scrollChatBottom();
}
function hideTypingBubble() {
  var t = document.getElementById('typingBubble');
  if (t) t.remove();
}

async function sendMessage() {
  if (state.defense) return;
  const input = document.getElementById('userInput');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';

  // Пузырь пользователя + "печатает"
  addUserMessage(text);
  state.thinking = true;
  showTypingBubble();

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: text})
    });
    const data = await resp.json();

    hideTypingBubble();
    addKairosMessage(data.response || 'Сэр, ответ не получен.');

    // 3D-синхронизация
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
      }
    } catch (e) {
      console.warn('[POSE]', e);
    }

    // Озвучка
    if (state.soundOn && data.audio_url) {
      const audio = document.getElementById('ttsAudio');
      audio.src = data.audio_url;
      audio.play().catch(e => console.log('audio err:', e));
    }
  } catch (e) {
    hideTypingBubble();
    addKairosMessage('Сэр, ошибка связи.');
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
    background: var(--bg-card);
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
  .history-list::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 3px; }
  .hist-item {
    padding: 8px 10px;
    margin: 6px 0;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.4;
    word-wrap: break-word;
  }
  .hist-del {
    float: right;
    color: #ff6666;
    cursor: pointer;
    font-size: 16px;
    padding: 0 6px;
    user-select: none;
  }
  .hist-del:hover { color: #ff3333; }

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

function deleteHistoryItem(index) {
    var pin = window.GENESIS_PIN || '';
    fetch('/api/history/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({pin: pin, index: index})
    })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.ok) {
        console.log('[HISTORY] Удалено:', d.removed);
        // Перезагрузить историю
        var pin2 = window.GENESIS_PIN || '';
        fetch('/api/history', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({pin: pin2})
        })
        .then(function(r) { return r.json(); })
        .then(function(dd) {
          if (dd.ok) renderHistory(dd.history || []);
        });
      } else {
        alert('Не удалось удалить: ' + (d.error || 'ошибка'));
      }
    })
    .catch(function(e) { console.warn('[HISTORY]', e); });
  }

  function renderHistory(items) {
  var list = document.getElementById('historyList');
  if (!items || !items.length) {
    list.innerHTML = '<div class="hist-item assistant">История пуста, Сэр.</div>';
    return;
  }
  var html = '';
  items.forEach(function(m, i) {
    var role = (m.role === 'user') ? 'user' : 'assistant';
    var time = (m.timestamp || '').replace('T', ' ').substring(0, 19);
    var text = (m.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    html += '<div class="hist-item ' + role + '" data-index="' + i + '">' + '<span class="hist-del" onclick="deleteHistoryItem(' + i + ')">✕</span>' + text +
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
    <script src="/static/genesis_app.js?v=14"></script>
<script src="/static/genesis_notes.js?v=3"></script>
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


@app.route("/api/news", methods=["GET"])
def api_news():
    """Новости из 3 источников (Habr, Onliner, BBC)."""
    import urllib.request, ssl as _ssl
    import xml.etree.ElementTree as _ET
    import re as _re
    import random as _random

    def _clean_cdata(s):
        if s is None: return ""
        s = s.strip()
        m = _re.match(r"<!\[CDATA\[(.*?)\]\]>$", s, _re.DOTALL)
        if m:
            s = m.group(1)
        return s.strip()

    def _pick_emoji(title):
        import re as _re2
        t = title.lower()
        def _has(words):
            for w in words:
                # Ищем как ОТДЕЛЬНОЕ СЛОВО (границы слов)
                if _re2.search(r"\b" + _re2.escape(w) + r"\b", t):
                    return True
            return False

        # 🚨 Экстренные / ЧП — проверяем ПЕРВЫМИ
        emergency = ["killed", "dies", "died", "dead", "death", "attack", "war",
                     "missile", "earthquake", "shooting", "crash",
                     "погиб", "погибло", "убит", "убито", "теракт", "война",
                     "катастроф", "взрыв", "авари", "пожар"]
        if _has(emergency): return "🚨"
        # 🤖 ИИ / нейросети
        if any(w in t for w in ["ai ", " ai", "ии ", " ии", "нейросет", "ml ", "llm", "gpt", "chatgpt"]): return "🤖"
        # 🔒 Безопасность
        if any(w in t for w in ["безопас", "взлом", "уязвим", "security", "hack"]): return "🔒"
        # 🎮 Игры
        if any(w in t for w in ["игр", "game", "гейм", "gaming", "playstation", "xbox"]): return "🎮"
        # 🔬 Наука / космос
        if any(w in t for w in ["наук", "физик", "космос", "астро", "science", "space", "nasa", "asteroid", "космонавт"]): return "🔬"
        # 🦠 Медицина / здоровье
        if any(w in t for w in ["медицин", "здоров", "health", "virus", "covid", "вакцин", "болезн"]): return "🦠"
        # 🌱 Экология / климат
        if any(w in t for w in ["эколог", "климат", "climate", "green", "природ", "carbon"]): return "🌱"
        # ⚽ Спорт
        if any(w in t for w in ["спорт", "sport", "football", "футбол", "чемпион", "олимп"]): return "⚽"
        # 💰 Финансы / экономика
        if any(w in t for w in ["курс", "финанс", "эконом", "economy", "market", "business",
                                  "dollar", "euro", "рубл", "цен", "инфляц", "imf"]): return "💰"
        # 🌍 Политика / мир
        if any(w in t for w in ["политик", "government", "politician", "election",
                                  "trump", "biden", "putin", "правительств", "президент"]): return "🌍"
        # 🛰 Технологии
        if any(w in t for w in ["технолог", "разработ", "код", "python", "javascript",
                                  "tech", "gadget", "smartphone", "apple", "samsung"]): return "🛰"
        # 📰 Дефолт
        return "📰"

    FEEDS = [
        {"url": "https://habr.com/ru/rss/articles/", "tag": "Хабр"},
        {"url": "https://tech.onliner.by/feed", "tag": "Onliner"},
        {"url": "http://feeds.bbci.co.uk/news/rss.xml", "tag": "BBC"},
    ]

    try:
        ctx = _ssl._create_unverified_context()
        all_news = []
        for feed in FEEDS:
            try:
                req = urllib.request.Request(feed["url"], headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                    xml_data = resp.read()
                root = _ET.fromstring(xml_data)
                items = root.findall(".//item")[:5]
                for it in items:
                    title = _clean_cdata(it.findtext("title"))
                    link = _clean_cdata(it.findtext("link"))
                    if not title or not link:
                        continue
                    all_news.append({
                        "title": title,
                        "link": link,
                        "emoji": _pick_emoji(title),
                        "tag": feed["tag"],
                    })
            except Exception as ex:
                print("[NEWS]", feed["tag"], ":", ex)
                continue
        _random.shuffle(all_news)
        return jsonify({"ok": True, "news": all_news[:10]})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500


@app.route("/api/space", methods=["GET"])
def api_space():
    """Фаза Луны + случайный факт о космосе."""
    import math as _math
    import datetime as _dt
    import random as _random
    try:
        # Синодический месяц = 29.530588853 дней
        # Опорная дата: новолуние 2000-01-06 18:14 UTC
        ref = _dt.datetime(2000, 1, 6, 18, 14)
        now = _dt.datetime.utcnow()
        diff_days = (now - ref).total_seconds() / 86400.0
        days_since = diff_days % 29.530588853
        phase = days_since / 29.530588853  # 0..1

        # 8 фаз
        if phase < 0.0625 or phase >= 0.9375:
            moon_emoji = "🌑"
            moon_name = "Новолуние"
        elif phase < 0.1875:
            moon_emoji = "🌒"
            moon_name = "Растущий серп"
        elif phase < 0.3125:
            moon_emoji = "🌓"
            moon_name = "Первая четверть"
        elif phase < 0.4375:
            moon_emoji = "🌔"
            moon_name = "Растущая Луна"
        elif phase < 0.5625:
            moon_emoji = "🌕"
            moon_name = "Полнолуние"
        elif phase < 0.6875:
            moon_emoji = "🌖"
            moon_name = "Убывающая Луна"
        elif phase < 0.8125:
            moon_emoji = "🌗"
            moon_name = "Последняя четверть"
        else:
            moon_emoji = "🌘"
            moon_name = "Убывающий серп"

        facts = [
            "Юпитер в 318 раз тяжелее Земли.",
            "Свет от Солнца идёт до Земли 8 минут 20 секунд.",
            "На Венере сутки длиннее года.",
            "Нейтронная звезда может весить как Солнце, но быть 20 км в диаметре.",
            "Чёрная дыра в центре Млечного Пути — 4 миллиона масс Солнца.",
            "Юпитер вращается быстрее всех планет — 10 часов на сутки.",
            "Сатурн — самая лёгкая планета: он бы плавал в воде.",
            "Луна удаляется от Земли на 3.8 см в год.",
            "Квазары ярче целых галактик в тысячи раз.",
            "Солнечная корона горячее поверхности Солнца в 200 раз.",
            "Ганимед (спутник Юпитера) больше Меркурия.",
            "Космос расширяется со скоростью ~70 км/с на мегапарсек.",
            "Марс — единственная планета, где дуют пылевые бури по всей планете.",
            "Комета Галлея вернётся в 2061 году.",
            "На Титане (спутник Сатурна) идут дожди из метана.",
            "Нейтронные звёзды генерируют магнитные поля в триллионы раз сильнее земного.",
            "Земля — единственное место, где известна жидкая вода на поверхности.",
            "Крабовидная туманность расширяется со скоростью 1500 км/с.",
            "В нашей Галактике — около 100 миллиардов звёзд.",
            "Во Вселенной больше звёзд, чем песчинок на всех пляжах Земли.",
            "Юпитер защищает Землю от комет своим гравитационным полем.",
            "Космический мусор на орбите Земли летит со скоростью 8 км/с.",
            "Меркурий — самая быстрая планета: 47 км/с вокруг Солнца.",
            "Уран вращается «на боку» — ось наклонена на 98°.",
        ]
        fact = _random.choice(facts)

        return jsonify({
            "ok": True,
            "moon_emoji": moon_emoji,
            "moon_name": moon_name,
            "fact": fact,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/currencies", methods=["GET"])
def api_currencies():
    """Курсы валют с НБРБ (USD, EUR, PLN)."""
    import urllib.request, urllib.error, json as _json, ssl as _ssl
    try:
        ctx = _ssl._create_unverified_context()
        result = {}
        codes = ["USD", "EUR", "PLN"]
        for code in codes:
            url = f"https://api.nbrb.by/exrates/rates/{code}?parammode=2"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            rate = data.get("Cur_OfficialRate", 0)
            scale = data.get("Cur_Scale", 1)
            # Курс за 1 единицу
            per_one = round(rate / scale, 4)
            result[code] = per_one

        return jsonify({
            "ok": True,
            "USD": result.get("USD", 0),
            "EUR": result.get("EUR", 0),
            "PLN": result.get("PLN", 0),
            "BYN": 1.00,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/weather", methods=["GET"])
def api_weather():
    """Погода в Гродно через OpenWeather."""
    import urllib.request, urllib.error, json as _json, ssl as _ssl
    try:
        key = _load_secret("OPENWEATHER_KEY")
        if not key:
            return jsonify({"ok": False, "error": "no_key"}), 500

        # Гродно: lat=53.6667, lon=23.8333 (точнее, чем по названию)
        lat = 53.6667
        lon = 23.8333
        url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"lat={lat}&lon={lon}&appid={key}&units=metric&lang=ru"
        )
        ctx = _ssl._create_unverified_context()
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = _json.loads(resp.read().decode("utf-8"))

        temp = round(data.get("main", {}).get("temp", 0))
        feels = round(data.get("main", {}).get("feels_like", 0))
        hum = data.get("main", {}).get("humidity", 0)
        desc = (data.get("weather", [{}])[0].get("description", "")).capitalize()
        icon_id = data.get("weather", [{}])[0].get("id", 800)

        # Эмодзи по коду OpenWeather
        def pick_icon(cid):
            if cid < 300: return "⛈"
            if cid < 400: return "🌧"
            if cid < 500: return "🌧"
            if cid < 600: return "🌧"
            if cid < 700: return "🌨"
            if cid < 800: return "🌫"
            if cid == 800: return "☀️"
            if cid == 801: return "🌤"
            if cid == 802: return "⛅"
            if cid == 803 or cid == 804: return "☁️"
            return "🌡"

        return jsonify({
            "ok": True,
            "city": "Гродно",
            "temp": temp,
            "feels": feels,
            "humidity": hum,
            "desc": desc,
            "emoji": pick_icon(icon_id),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/change_pin", methods=["POST"])
def api_change_pin():
    """Меняет PIN. Сохраняет в ~/.genesis_pin."""
    global PIN_DEFAULT
    import os as _os
    try:
        data = request.get_json(force=True, silent=True) or {}
        new_pin = str(data.get("pin", "")).strip()
        if not new_pin or len(new_pin) > 32:
            return jsonify({"ok": False, "error": "invalid_pin"}), 400

        pin_file = _os.path.expanduser("~/.genesis_pin")
        with open(pin_file, "w", encoding="utf-8") as f:
            f.write(new_pin)

        PIN_DEFAULT = new_pin  # обновляем в памяти
        print(f"[DOOM WEB] PIN изменён.")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/history", methods=["POST"])
def api_history():
    """Возвращает историю чата после проверки PIN."""
    import json as _json, os as _os
    try:
        data = request.get_json(force=True, silent=True) or {}
        pin = str(data.get("pin", ""))
        if pin != PIN_DEFAULT:
            return jsonify({"ok": False, "error": "wrong_pin"}), 403

        mem_path = _os.path.expanduser("~/genesis_memory.json")
        if not _os.path.exists(mem_path):
            return jsonify({"ok": True, "history": [], "total": 0})

        with open(mem_path, "r", encoding="utf-8") as f:
            mem = _json.load(f)

        conv = mem.get("conversation", [])
        return jsonify({"ok": True, "history": conv, "total": len(conv)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/history/delete", methods=["POST"])
def api_history_delete():
    """Удаляет одну запись по индексу."""
    import json as _json, os as _os
    try:
        data = request.get_json(force=True, silent=True) or {}
        pin = str(data.get("pin", ""))
        if pin != PIN_DEFAULT:
            return jsonify({"ok": False, "error": "wrong_pin"}), 403

        index = int(data.get("index", -1))
        mem_path = _os.path.expanduser("~/genesis_memory.json")
        if not _os.path.exists(mem_path):
            return jsonify({"ok": False, "error": "no_memory"}), 404

        with open(mem_path, "r", encoding="utf-8") as f:
            mem = _json.load(f)

        conv = mem.get("conversation", [])
        if index < 0 or index >= len(conv):
            return jsonify({"ok": False, "error": "bad_index"}), 400

        removed = conv.pop(index)
        mem["conversation"] = conv
        with open(mem_path, "w", encoding="utf-8") as f:
            _json.dump(mem, f, ensure_ascii=False, indent=2)

        return jsonify({"ok": True, "removed": removed, "total": len(conv)})
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

        mem_path = _os.path.expanduser("~/genesis_memory.json")
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


@app.route("/api/wiki", methods=["GET"])
def api_wiki():
    import urllib.parse
    import urllib.request
    import json as _json

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty query"})

    def _wiki_get(url):
        req = urllib.request.Request(url, headers={"User-Agent": "GENESIS-KAIROS/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return _json.loads(resp.read().decode("utf-8"))

    # 1. Opensearch — нормализация заголовка
    title = q
    normalized = False
    try:
        os_url = ("https://ru.wikipedia.org/w/api.php?action=opensearch&format=json"
                  "&limit=1&search=" + urllib.parse.quote(q))
        os_data = _wiki_get(os_url)
        if isinstance(os_data, list) and len(os_data) >= 2 and os_data[1]:
            title = os_data[1][0]
            normalized = True
    except Exception:
        pass

    # 1.5. Fallback через полный поиск (srsearch) — если opensearch не справился
    if not normalized:
        try:
            sr_url = ("https://ru.wikipedia.org/w/api.php?action=query&format=json"
                      "&list=search&srlimit=1&srsearch=" + urllib.parse.quote(q))
            sr_data = _wiki_get(sr_url)
            sr_hits = (sr_data.get("query") or {}).get("search") or []
            if sr_hits:
                title = sr_hits[0].get("title") or title
                normalized = True
        except Exception:
            pass

    # 2. Summary по нормализованному заголовку
    def _fetch_summary(t):
        u = ("https://ru.wikipedia.org/api/rest_v1/page/summary/"
             + urllib.parse.quote(t.replace(" ", "_")))
        return _wiki_get(u)

    data = None
    err = None
    try:
        data = _fetch_summary(title)
    except Exception as e:
        err = str(e)
        # fallback: сырой q
        if title != q:
            try:
                data = _fetch_summary(q)
                title = q
                normalized = False
                err = None
            except Exception as e2:
                err = str(e2)

    if data is None:
        return jsonify({"ok": False, "error": err or "not found"})

    if data.get("type") == "disambiguation":
        return jsonify({"ok": False, "error": "disambiguation", "title": title})

    extract = data.get("extract") or ""
    if not extract:
        return jsonify({"ok": False, "error": "no extract", "title": title})

    thumb = ""
    if isinstance(data.get("thumbnail"), dict):
        thumb = data["thumbnail"].get("source") or ""

    page_url = ""
    cu = data.get("content_urls")
    if isinstance(cu, dict) and isinstance(cu.get("desktop"), dict):
        page_url = cu["desktop"].get("page") or ""

    return jsonify({
        "ok": True,
        "title": data.get("title") or title,
        "extract": extract,
        "thumbnail": thumb,
        "url": page_url,
        "normalized": normalized,
    })


@app.route("/api/fandom", methods=["GET"])
def api_fandom():
    import urllib.parse
    import urllib.request
    import json as _json
    import re as _re

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty query"})

    base = "https://marvel.fandom.com"

    def _fg(url):
        req = urllib.request.Request(url, headers={"User-Agent": "GENESIS-KAIROS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return _json.loads(resp.read().decode("utf-8"))

    # 1. Поиск — получаем правильный заголовок
    title = q
    try:
        s_url = (base + "/api.php?action=query&format=json&list=search&srlimit=1"
                 "&srsearch=" + urllib.parse.quote(q))
        s_data = _fg(s_url)
        hits = (s_data.get("query") or {}).get("search") or []
        if hits:
            title = hits[0].get("title") or title
        else:
            return jsonify({"ok": False, "error": "not found"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

    # 2. Статья — parse section=0
    try:
        p_url = (base + "/api.php?action=parse&format=json&prop=text&section=0"
                 "&page=" + urllib.parse.quote(title.replace(" ", "_")))
        p_data = _fg(p_url)
        html = (p_data.get("parse") or {}).get("text", {}).get("*", "")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

    if not html:
        return jsonify({"ok": False, "error": "no text"})

    # 3. Чистим HTML
    text = _re.sub(r"<script[^>]*>.*?</script>", "", html, flags=_re.S)
    text = _re.sub(r"<style[^>]*>.*?</style>", "", text, flags=_re.S)
    text = _re.sub(r"<[^>]+>", " ", text)
    # HTML-entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    # base64 мусор
    text = _re.sub(r"data:image/[^\s]+", "", text)
    # Сжимаем пробелы
    text = _re.sub(r"\s+", " ", text).strip()

    if len(text) < 30:
        return jsonify({"ok": False, "error": "text too short"})

    if len(text) > 600:
        text = text[:600].rsplit(" ", 1)[0] + "..."

    page_url = base + "/wiki/" + urllib.parse.quote(title.replace(" ", "_"))

    return jsonify({
        "ok": True,
        "title": title,
        "extract": text,
        "url": page_url,
    })


# ==================== ЗАМЕТКИ / НАПОМИНАНИЯ / ДНЕВНИК ====================
import os as _os
import json as _json
import time as _time

NOTES_FILE = _os.path.expanduser("~/genesis_notes.json")

def _notes_load():
    if not _os.path.exists(NOTES_FILE):
        return {"notes": [], "reminders": [], "diary": []}
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            data = _json.load(f)
        for k in ("notes", "reminders", "diary"):
            data.setdefault(k, [])
        return data
    except Exception:
        return {"notes": [], "reminders": [], "diary": []}

def _notes_save(data):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        _json.dump(data, f, ensure_ascii=False, indent=2)

def _notes_next_id(items):
    if not items:
        return 1
    return max((it.get("id", 0) for it in items), default=0) + 1


@app.route("/api/notes", methods=["GET"])
def api_notes_get():
    return jsonify(_notes_load())


@app.route("/api/notes/add", methods=["POST"])
def api_notes_add():
    data = request.get_json() or {}
    ntype = (data.get("type") or "notes").strip()
    text = (data.get("text") or "").strip()
    if ntype not in ("notes", "reminders", "diary"):
        return jsonify({"ok": False, "error": "bad type"})
    if not text:
        return jsonify({"ok": False, "error": "empty text"})

    store = _notes_load()
    item = {
        "id": _notes_next_id(store[ntype]),
        "text": text,
        "ts": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if ntype == "reminders":
        item["when"] = (data.get("when") or "").strip()
        item["notified"] = False
    if ntype == "diary":
        item["date"] = _time.strftime("%Y-%m-%d")

    store[ntype].append(item)
    _notes_save(store)
    return jsonify({"ok": True, "item": item})


@app.route("/api/notes/delete", methods=["POST"])
def api_notes_delete():
    data = request.get_json() or {}
    ntype = (data.get("type") or "").strip()
    nid = data.get("id")
    if ntype not in ("notes", "reminders", "diary"):
        return jsonify({"ok": False, "error": "bad type"})
    try:
        nid = int(nid)
    except Exception:
        return jsonify({"ok": False, "error": "bad id"})

    store = _notes_load()
    before = len(store[ntype])
    store[ntype] = [it for it in store[ntype] if it.get("id") != nid]
    after = len(store[ntype])
    _notes_save(store)
    return jsonify({"ok": True, "removed": before - after})


@app.route("/api/youtube", methods=["GET"])
def api_youtube():
    import urllib.parse
    import urllib.request
    import json as _json

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty query"})

    key = _load_secret("GOOGLE_CSE_KEY")
    if not key:
        return jsonify({"ok": False, "error": "no key"})

    try:
        url = ("https://www.googleapis.com/youtube/v3/search"
               "?part=snippet&type=video&maxResults=3&key="
               + urllib.parse.quote(key)
               + "&q=" + urllib.parse.quote(q))
        req = urllib.request.Request(url, headers={"User-Agent": "GENESIS-KAIROS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

    items = []
    for it in (data.get("items") or [])[:3]:
        sn = it.get("snippet") or {}
        vid = (it.get("id") or {}).get("videoId")
        if not vid:
            continue
        items.append({
            "title": sn.get("title") or "",
            "channel": sn.get("channelTitle") or "",
            "url": "https://www.youtube.com/watch?v=" + vid,
            "thumb": ((sn.get("thumbnails") or {}).get("default") or {}).get("url") or "",
        })

    if not items:
        return jsonify({"ok": False, "error": "no results"})

    return jsonify({"ok": True, "items": items})


# ==================== СВЯЗЬ С ТЕЛЕФОНОМ (Termux:API) ====================
import subprocess as _sp
import platform as _plat
import os as _os_p
import json as _json_p

def _is_termux():
    return _os_p.path.exists("/data/data/com.termux/files/usr")

def _run_termux(cmd_list, timeout=10):
    if not _is_termux():
        return None, "not termux"
    try:
        r = _sp.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return None, r.stderr.strip() or "cmd failed"
        return r.stdout.strip(), None
    except Exception as e:
        return None, str(e)


@app.route("/api/phone/battery", methods=["GET"])
def api_phone_battery():
    if not _is_termux():
        return jsonify({"ok": False, "error": "not termux"})
    out, err = _run_termux(["termux-battery-status"])
    if err:
        return jsonify({"ok": False, "error": err})
    try:
        data = _json_p.loads(out)
    except Exception as e:
        return jsonify({"ok": False, "error": "parse: " + str(e)})
    return jsonify({
        "ok": True,
        "percent": data.get("percentage"),
        "plugged": data.get("plugged"),
        "status": data.get("status"),
        "temperature": data.get("temperature"),
        "health": data.get("health"),
    })


@app.route("/api/phone/volume", methods=["GET"])
def api_phone_volume():
    if not _is_termux():
        return jsonify({"ok": False, "error": "not termux"})
    out, err = _run_termux(["termux-volume"])
    if err:
        return jsonify({"ok": False, "error": err})
    try:
        data = _json_p.loads(out)
    except Exception as e:
        return jsonify({"ok": False, "error": "parse: " + str(e)})
    streams = {}
    for s in data:
        streams[s.get("stream")] = {
            "volume": s.get("volume"),
            "max": s.get("max_volume"),
        }
    return jsonify({"ok": True, "streams": streams})


@app.route("/api/phone/command", methods=["POST"])
def api_phone_command():
    data = request.get_json() or {}
    cmd = (data.get("cmd") or "").strip().lower()
    if not cmd:
        return jsonify({"ok": False, "error": "empty cmd"})

    if not _is_termux():
        return jsonify({"ok": False, "error": "not termux"})

    if cmd in ("battery", "батарея", "заряд", "зарядка"):
        out, err = _run_termux(["termux-battery-status"])
        if err:
            return jsonify({"ok": False, "error": err})
        try:
            d = _json_p.loads(out)
        except Exception as e:
            return jsonify({"ok": False, "error": "parse: " + str(e)})
        status = "заряжается" if "CHARGING" in (d.get("status") or "") else "разряжается"
        return jsonify({
            "ok": True,
            "reply": "Батарея: " + str(d.get("percentage")) + "%, " + status +
                     ", температура " + str(d.get("temperature")) + "°C."
        })

    if cmd in ("volume", "громкость"):
        out, err = _run_termux(["termux-volume"])
        if err:
            return jsonify({"ok": False, "error": err})
        try:
            data2 = _json_p.loads(out)
        except Exception as e:
            return jsonify({"ok": False, "error": "parse: " + str(e)})
        parts = []
        for s in data2:
            name = s.get("stream")
            if name in ("music", "ring", "notification"):
                parts.append(name + ": " + str(s.get("volume")) + "/" + str(s.get("max_volume")))
        return jsonify({"ok": True, "reply": "Громкость — " + " · ".join(parts)})

    return jsonify({"ok": False, "error": "unknown cmd"})


@app.route("/api/phone/torch", methods=["POST"])
def api_phone_torch():
    data = request.get_json() or {}
    action = (data.get("action") or "").strip().lower()
    if action not in ("on", "off"):
        return jsonify({"ok": False, "error": "action must be on/off"})
    if not _is_termux():
        return jsonify({"ok": False, "error": "not termux"})
    out, err = _run_termux(["termux-torch", action])
    if err:
        return jsonify({"ok": False, "error": err})
    return jsonify({"ok": True, "reply": "Фонарик " + ("включён" if action == "on" else "выключен") + ", Сэр."})


@app.route("/api/phone/volume/set", methods=["POST"])
def api_phone_volume_set():
    data = request.get_json() or {}
    stream = (data.get("stream") or "music").strip()
    try:
        level = int(data.get("level", 5))
    except Exception:
        return jsonify({"ok": False, "error": "level must be int"})
    if not _is_termux():
        return jsonify({"ok": False, "error": "not termux"})
    out, err = _run_termux(["termux-volume", stream, str(level)])
    if err:
        return jsonify({"ok": False, "error": err})
    return jsonify({"ok": True, "reply": "Громкость " + stream + " = " + str(level) + ", Сэр."})


# Карта популярных приложений (имя → package)
_APPS_MAP = {
    "telegram": "org.telegram.messenger/org.telegram.ui.LaunchActivity",
    "телеграм": "org.telegram.messenger/org.telegram.ui.LaunchActivity",
    "телеграмм": "org.telegram.messenger/org.telegram.ui.LaunchActivity",
    "youtube": "com.google.android.youtube/com.google.android.apps.youtube.app.WatchWhileActivity",
    "ютуб": "com.google.android.youtube/com.google.android.apps.youtube.app.WatchWhileActivity",
    "whatsapp": "com.whatsapp/com.whatsapp.Main",
    "ватсап": "com.whatsapp/com.whatsapp.Main",
    "вотсап": "com.whatsapp/com.whatsapp.Main",
    "instagram": "com.instagram.android/com.instagram.android.activity.MainTabActivity",
    "инстаграм": "com.instagram.android/com.instagram.android.activity.MainTabActivity",
    "tiktok": "com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.SplashActivity",
    "тикток": "com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.SplashActivity",
    "viber": "com.viber.voip/com.viber.voip.WelcomeActivity",
    "вайбер": "com.viber.voip/com.viber.voip.WelcomeActivity",
    "discord": "com.discord/com.discord.main.MainActivity",
    "дискорд": "com.discord/com.discord.main.MainActivity",
    "spotify": "com.spotify.music/com.spotify.music.MainActivity",
    "спотифай": "com.spotify.music/com.spotify.music.MainActivity",
    "chrome": "com.android.chrome/com.google.android.apps.chrome.Main",
    "хром": "com.android.chrome/com.google.android.apps.chrome.Main",
    "браузер": "com.android.chrome/com.google.android.apps.chrome.Main",
    "browser": "com.android.chrome/com.google.android.apps.chrome.Main",
    "settings": "com.android.settings/com.android.settings.Settings",
    "настройки": "com.android.settings/com.android.settings.Settings",
    "calculator": "com.android.calculator2/com.android.calculator2.Calculator",
    "калькулятор": "com.android.calculator2/com.android.calculator2.Calculator",
    "maps": "com.google.android.apps.maps/com.google.android.maps.MapsActivity",
    "карты": "com.google.android.apps.maps/com.google.android.maps.MapsActivity",
    "gmail": "com.google.android.gm/com.google.android.gm.ConversationListActivityGmail",
    "почта": "com.google.android.gm/com.google.android.gm.ConversationListActivityGmail",
}


@app.route("/api/phone/open", methods=["POST"])
def api_phone_open():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip().lower()
    if not name:
        return jsonify({"ok": False, "error": "empty name"})
    if not _is_termux():
        return jsonify({"ok": False, "error": "not termux"})

    pkg = _APPS_MAP.get(name) or name

    try:
        r = _sp.run(["am", "start", "--user", "0", "-n", pkg],
                    capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip()[:300]
            return jsonify({"ok": False, "error": "am: " + err})
        return jsonify({"ok": True, "reply": "Открываю " + name + ", Сэр."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"response": "..."})
    
    if GLOBAL_CORE is None:
        return jsonify({"response": "Сэр, ядро не подключено."})
    
    context = data.get("context", "").strip()
    full_text = (context + "\n\nВопрос: " + text) if context else text
    
    try:
        # 1. Получаем ответ от ядра
        response = GLOBAL_CORE.ask(full_text)
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
