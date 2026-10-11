# Project Genesis

> AI-powered robotic arm assistant (KAIROS) running on Android + ESP32.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Android-green)

---

## What is Project Genesis?

**Project Genesis** is a personal research project by a 15-year-old developer. It combines a **large language model assistant (KAIROS)**, **voice and text control in Russian**, a **3D-robotic arm visualization**, and an **ESP32-controlled physical robot arm**.

The goal: build a real AI assistant that can think, answer, and control physical hardware — like JARVIS, but on a budget and built from scratch.

---

## Features

- **AI assistant (KAIROS)** powered by LLM (Qwen 3.8 Max via OpenRouter).
- **Voice & text control** in Russian (Web Speech API).
- **6-DOF robotic arm** visualization (Three.js, OrbitControls).
- **Real-time angle commands**: base, shoulder, elbow, wrist (pitch/roll), gripper.
- **Safe limits** and validation for each joint.
- **Secure chat history** with PIN protection.
- **PWA** — installable on Android home screen.
- **3D model synchronized** with commands.
- **ESP32 integration** (hardware in development).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14, Flask |
| LLM | Qwen 3.8 Max (OpenRouter API) |
| Frontend | HTML, CSS, JavaScript, Three.js |
| Voice | Web Speech API, Android TTS |
| Hardware | ESP32-S3, PCA9685, servos (DS3240, MG996R) |
| Firmware | MicroPython |
| Runtime | Termux (Android) |
| Deployment | PWA (manifest + Service Worker) |

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Termux (Android)                       │
│                                         │
│  doom_core.py   →  LLM (OpenRouter)     │
│       ↓                                 │
│  doom_web.py    →  Web UI (Flask)       │
│       ↓                                 │
│  esp_bridge.py  ─── UDP ────┐           │
└─────────────────────────────┼───────────┘
                              │
                         WiFi (LAN)
                              │
                              ↓
┌─────────────────────────────────────────┐
│  ESP32-S3 (MicroPython)                 │
│       ↓                                 │
│  PCA9685 (I2C) → 6 servos               │
└─────────────────────────────────────────┘
```

---

## Installation

### Requirements

- Android device with Termux installed.
- Termux:API app (for hardware features).
- Python 3.10+.
- An OpenRouter API key (free).

### Steps

```bash
# 1. Install dependencies
pkg update && pkg upgrade
pkg install python mpv ffmpeg termux-api git

# 2. Clone the repository
git clone https://github.com/ironx987-spec/project-genesis.git
cd project-genesis

# 3. Install Python packages
pip install flask edge-tts

# 4. Set up your OpenRouter key
echo "OPENROUTER_KEY=sk-or-v1-YOUR_KEY_HERE" > ~/.doom_secrets

# 5. Set up PIN
echo "your_pin" > ~/.doom_pin

# 6. Run
python3 doom_launcher.py
```

Then open **http://127.0.0.1:5000** in your browser.

---

## Usage

### Text commands

| Command | Action |
|---|---|
| `плечо 30` | Shoulder → 30° |
| `локоть 120` | Elbow → 120° |
| `база 45` | Base → 45° |
| `схват 100` | Gripper → close |
| `домой` | Return to home position |

### Voice

Press the microphone button and speak in Russian.

### Web interface

- **Tab 1 (Основное)** — chat with KAIROS.
- **Tab 2 (Управление)** — manual control (sliders + 3D view).

---

## Roadmap

- [x] LLM integration (KAIROS)
- [x] 3D robotic arm visualization
- [x] Text & voice commands
- [x] PWA (installable app)
- [x] Secure chat history with PIN
- [ ] ESP32 hardware integration
- [ ] Weather, news, reminders
- [ ] Local LLM (offline mode)
- [ ] Computer vision (ESP32-CAM)
- [ ] Sensor integration (VL53L0X, MPU6050, FSR402)
- [ ] English localization

---

## Author

**Aleksei Zverzhevich** — 15 years old.

- GitHub: [@ironx987-spec](https://github.com/ironx987-spec)
- Project: [project-genesis](https://github.com/ironx987-spec/project-genesis)

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
