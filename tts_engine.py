# tts_engine.py — KAIROS TTS через Android (termux-tts-speak)
# Без эффектов Дума. Мгновенно, без интернета.
import subprocess
import re


class TTSEngine:
    def __init__(self, engine="com.google.android.tts"):
        self.engine = engine  # можно не указывать — берётся из настроек Android

    def _clean_text(self, text: str) -> str:
        """Убирает служебные символы, которые плохо звучат."""
        text = re.sub(r'[*_#>`~|]', '', text)
        text = re.sub(r'[{}<>\[\]]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Слишком длинный текст — обрезаем (Android TTS не любит огромные фразы)
        if len(text) > 400:
            text = text[:400] + "..."
        return text

    def _cache_path(self, text: str) -> str:
        """Заглушка для совместимости с старым API. Android TTS не кэширует."""
        return ""

    def speak(self, text: str):
        """Озвучивает текст через Android TTS."""
        if not text:
            return
        safe = self._clean_text(text)
        if not safe:
            return

        # termux-tts-speak — блокирующий вызов (ждёт окончания речи)
        # Для ассинхронности можно убрать ожидание, но пока оставим так.
        try:
            subprocess.run(
                [
                    "termux-tts-speak",
                    "-e", "com.google.android.tts",
                    "-l", "ru",
                    "-p", "0.95",   # тон чуть ниже — солиднее
                    "-r", "0.95",   # скорость чуть медленнее — Джарвис-стиль
                    "-s", "MUSIC",  # через медиапоток — не «уведомление»
                    safe,
                ],
                timeout=60,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            print("[TTS] таймаут озвучки")
        except FileNotFoundError:
            print("[TTS ERR] termux-tts-speak не найден. Установи: pkg install termux-api + приложение Termux:API")
        except Exception as e:
            print(f"[TTS ERR] {e}")


if __name__ == "__main__":
    tts = TTSEngine()
    tts.speak("Привет, Сэр. Я KAIROS. Проверка голоса.")
    tts.speak("Все системы работают в штатном режиме.")
