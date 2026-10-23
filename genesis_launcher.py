"""
genesis_launcher.py — Запуск KAIROSа: ядро + веб-интерфейс.
"""
import sys
import os

sys.path.insert(0, os.path.expanduser("~"))

from genesis_core import GenesisCore
from genesis_web import run_web

import threading
import time as _time
import json as _json
import os as _os
import subprocess as _sp

_NOTES_FILE = _os.path.expanduser("~/genesis_notes.json")

def _volume_loop():
    """Каждые 30 секунд — обновляем кеш громкости."""
    while True:
        try:
            r = _sp.run(["termux-volume"], capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                data = _json.loads(r.stdout)
                with open(_os.path.expanduser("~/volume_cache.json"), "w", encoding="utf-8") as f:
                    _json.dump({"ts": _time.time(), "data": data}, f, ensure_ascii=False)
        except Exception as e:
            print("[VOLUME] loop error:", e)
        _time.sleep(30)


def _volume_loop():
    """Каждые 30 секунд — обновляем кеш громкости."""
    while True:
        try:
            r = _sp.run(["termux-volume"], capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                data = _json.loads(r.stdout)
                with open(_os.path.expanduser("~/volume_cache.json"), "w", encoding="utf-8") as f:
                    _json.dump({"ts": _time.time(), "data": data}, f, ensure_ascii=False)
        except Exception as e:
            print("[VOLUME] loop error:", e)
        _time.sleep(30)


def _battery_loop():
    """Каждые 30 секунд — обновляем кеш батареи."""
    while True:
        try:
            r = _sp.run(["termux-battery-status"], capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                data = _json.loads(r.stdout)
                with open(_os.path.expanduser("~/battery_cache.json"), "w", encoding="utf-8") as f:
                    _json.dump({"ts": _time.time(), "data": data}, f, ensure_ascii=False)
        except Exception as e:
            print("[BATTERY] loop error:", e)
        _time.sleep(30)


def _reminder_loop():
    """Раз в 30 секунд проверяем напоминания и шлём уведомления."""
    while True:
        try:
            if _os.path.exists(_NOTES_FILE):
                with open(_NOTES_FILE, "r", encoding="utf-8") as f:
                    data = _json.load(f)
                reminders = data.get("reminders", [])
                now = _time.strftime("%Y-%m-%d %H:%M")
                changed = False

                for r in reminders:
                    if r.get("notified"):
                        continue
                    when = (r.get("when") or "").strip()
                    if not when:
                        continue
                    # Сравниваем по минутам: "YYYY-MM-DD HH:MM"
                    # Если when короче (только дата) — добавляем " 00:00"
                    key = when[:16]
                    if key <= now:
                        # Пора уведомить
                        try:
                            _sp.run([
                                "termux-notification",
                                "--title", "KAIROS · Напоминание",
                                "--content", r.get("text", ""),
                                "--priority", "high",
                            ], timeout=10)
                        except Exception as e:
                            print("[REMINDER] notification error:", e)
                        r["notified"] = True
                        changed = True

                if changed:
                    with open(_NOTES_FILE, "w", encoding="utf-8") as f:
                        _json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[REMINDER] loop error:", e)
        _time.sleep(30)


def main():
    print("=" * 60)
    print("  GENESIS — Запуск системы")
    print("=" * 60)

    # 1. Создать ядро
    print("[LAUNCHER] Инициализация ядра...")
    core = GenesisCore()
    core.voice_web = True  # веб сам играет mp3
    print("[LAUNCHER] Ядро готово")

    # Запускаем фоновый поток напоминаний
    t = threading.Thread(target=_reminder_loop, daemon=True)
    t.start()
    print("[LAUNCHER] Поток напоминаний запущен.")

    # Запускаем фоновый поток батареи (кеш раз в 30 сек)
    t2 = threading.Thread(target=_battery_loop, daemon=True)
    t2.start()
    print("[LAUNCHER] Поток батареи запущен.")

    # Запускаем фоновый поток громкости (кеш раз в 30 сек)
    t3 = threading.Thread(target=_volume_loop, daemon=True)
    t3.start()
    print("[LAUNCHER] Поток громкости запущен.")

    # Запускаем фоновый поток громкости (кеш раз в 30 сек)
    t3 = threading.Thread(target=_volume_loop, daemon=True)
    t3.start()
    print("[LAUNCHER] Поток громкости запущен.")

    # 2. Запустить веб
    print("[LAUNCHER] Запуск веб-интерфейса...")
    print("[LAUNCHER] Открой в браузере: http://127.0.0.1:5000")
    print("=" * 60)
    run_web(core=core, bridge=None, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
