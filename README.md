# Project Genesis

> AI-powered robotic arm assistant (KAIROS) running on Android + ESP32.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Android-green)

---

## What is Project Genesis?

**Project Genesis** is a personal research project by a **15-year-old developer** from Hrodna, Belarus. It combines a **large language model assistant (KAIROS)**, **voice and text control in Russian**, a **3D-robotic arm visualization**, and an **ESP32-controlled physical robot arm**.

The goal: build a real AI assistant that can think, answer, control physical hardware — like JARVIS, but on a budget and built from scratch.

---

## Features

### AI & Chat
- **KAIROS** — AI assistant powered by **Qwen 3.8 Max** (OpenRouter).
- Personality: calm, smart, dry humor. Address: **"Сэр"**.
- **Memory** (LongTerm + UserMemory).
- **Chat with bubbles** (messenger style).
- **Voice input** (Web Speech API, Russian).

### Live Data (in chat + Info tab)
- **Weather** — OpenWeather (Hrodna, BY).
- **Currencies** — NBRB (USD, EUR, PLN, BYN).
- **News** — Habr + Onliner + BBC (RSS, 10 mixed).
- **Space** — Moon phase + random fact.

### Search
- **Wikipedia** (srsearch — handles Russian cases).
- **Fandom** (Marvel, games).
- **YouTube** (3 videos for "найди видео про X").
- Links open in new tab.

### Notes / Reminders / Diary
- **Notes** — add, delete, list (JSON).
- **Reminders** — "напомни X в YYYY-MM-DD HH:MM" → Termux notification.
- **Diary** — entries by date.

### Phone (Termux:API)
- **Battery** — status + cache 30 sec.
- **Volume** — get/set (music, ring, alarm).
- **Open apps** — via `am start`.

### UI
- **5 tabs** — 💬 Main, 🦾 Control, 📰 Info, 📝 Notes, ⚙️ Settings.
- **3D 6-DOF robotic arm** (Three.js + OrbitControls).
- **6 sliders** + HOME button.
- **Defense mode** 🛡️ — red star + PIN.
- **Chat history** with PIN + delete individual entries.
- **New chat** (⟳).
- **PWA** — installable, blue star icon.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, Flask |
| LLM | Qwen 3.8 Max (OpenRouter) |
| Frontend | HTML, CSS, JS, Three.js |
| Voice | Web Speech API |
| Hardware | ESP32-S3, PCA9685, DS3240 + MG996R servos |
| Firmware | MicroPython |
| Runtime | Termux (Android) |
| Deployment | PWA (manifest + Service Worker) |

---

## Architecture

cd ~/genesis-repo
cp .gitignore .gitignore.bak

cat << 'EOF' > .gitignore
# Secrets
.genesis_secrets
.genesis_pin
.doom_secrets
.doom_pin
*_key.txt

# User data
genesis_memory.json
genesis_user_memory.json
genesis_notes.json
doom_memory.json
doom_user_memory.json

# Cache / logs
genesis_tts_cache/
doom_tts_cache/
genesis_system.log
doom_system.log
__pycache__/
*.pyc

# PID
*.pid

# Backups
*.bak
*.bak_*
*.bak[0-9]*

# Temporary
test_*.mp3
test_*.wav
test_*.json
_new_prompt.txt

# OS / IDE
.DS_Store
.vscode/
.idea/
