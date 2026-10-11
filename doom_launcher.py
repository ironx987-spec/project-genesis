"""
doom_launcher.py — Запуск KAIROSа: ядро + веб-интерфейс.
"""
import sys
import os

sys.path.insert(0, os.path.expanduser("~"))

from doom_core import GenesisCore
from doom_web import run_web


def main():
    print("=" * 60)
    print("  GENESIS — Запуск системы")
    print("=" * 60)

    # 1. Создать ядро
    print("[LAUNCHER] Инициализация ядра...")
    core = GenesisCore()
    core.voice_web = True  # веб сам играет mp3
    print("[LAUNCHER] Ядро готово")

    # 2. Запустить веб
    print("[LAUNCHER] Запуск веб-интерфейса...")
    print("[LAUNCHER] Открой в браузере: http://127.0.0.1:5000")
    print("=" * 60)
    run_web(core=core, bridge=None, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
