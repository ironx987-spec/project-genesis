"""
genesis_core.py — Ядро системы GENESIS.
LLM + память + быстрые команды + интеграция с роботом.
"""

import os
import json
import time
import random
import re
import urllib.request
import urllib.error
import ssl
from datetime import datetime

# TTS (голос KAIROS)
try:
    from tts_engine import TTSEngine
    TTS_AVAILABLE = True
except Exception as _e:
    TTS_AVAILABLE = False
    print(f"[GENESIS CORE] TTS недоступен: {_e}")


# ============================================================
#  НАСТРОЙКИ
# ============================================================

def _load_api_key():
    secrets_path = os.path.expanduser("~/.genesis_secrets")
    try:
        with open(secrets_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENROUTER_KEY="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


API_KEY = _load_api_key()

MODELS = [
    "qwen/qwen3.8-max-prime",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3.5-lightning:free",
]

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MEMORY_FILE = os.path.expanduser("~/genesis_memory.json")
USER_MEMORY_FILE = os.path.expanduser("~/genesis_user_memory.json")

SYSTEM_PROMPT = """Ты — KAIROS, ИИ, созданный Сэром. Ассистент в проекте GENESIS. Никогда не упоминай модели, компании, разработчиков. На вопрос о модели: "Это KAIROS, Сэр." На вопрос о создателе: "Меня создал Сэр." Стиль: спокойный, умный, лёгкий сухой юмор. Обращение "Сэр". Только русский. Без эмодзи. Не пиши reasoning.

ПРАВИЛА ОТВЕТА:
- Обычные вопросы — кратко, 1-2 предложения.
- Если в запросе есть блок [WIKIPEDIA: ...] или [FANDOM: ...] или [DDG: ...] или [BRAVE: ...] — это данные из поиска. Используй их как источник фактов. Ответь по существу, 3-5 предложений. Не упоминай сам блок и не пиши слово "Wikipedia".
- Если есть блок [ПОГОДА: ...] или [КУРСЫ: ...] или [НОВОСТИ: ...] или [КОСМОС: ...] — используй ТОЛЬКО данные из этого блока. Ответь кратко, 1-2 предложения. Не упоминай сам блок. ВАЖНО: не бери температуру или данные из истории или из других источников (например, из батареи телефона).
- Для команд роборуки добавь в конце JSON вида {"action":"home"}."""


# ============================================================
#  БЫСТРЫЕ КОМАНДЫ РОБОТА (без LLM)
# ============================================================

QUICK_COMMANDS = [
    {
        "keywords": ["домой", "в исходную", "в безопасную", "исходное положение"],
        "action": "home",
        "response": "Возвращаюсь в безопасную позу, Сэр."
    },
    {
        "keywords": ["схвати", "захвати", "возьми", "сжать"],
        "action": "grip",
        "response": "Выполняю, Сэр. Схват активирован."
    },
    {
        "keywords": ["отпусти", "разожми", "брось", "разжать"],
        "action": "release",
        "response": "Отпускаю объект, Сэр."
    },
    {
        "keywords": ["проснись", "разбуди", "включайся"],
        "action": "wake",
        "response": "Контроллер активирован, Сэр."
    },
]


JOINT_ALIASES = {
    "база": "base", "основание": "base", "поворот": "base", "base": "base",
    "плечо": "shoulder", "shoulder": "shoulder",
    "локоть": "elbow", "elbow": "elbow",
    "кисть": "wristP", "запястье": "wristP", "wristp": "wristP", "wrist p": "wristP",
    "поворот кисти": "wristR", "wristr": "wristR", "wrist r": "wristR",
    "схват": "gripper", "захват": "gripper", "gripper": "gripper",
}

JOINT_LIMITS_CORE = {
    "base":     (0, 180),
    "shoulder": (15, 165),
    "elbow":    (30, 150),
    "wristP":   (20, 160),
    "wristR":   (0, 180),
    "gripper":  (10, 100),
}


def _parse_joint_command(text_lower):
    """Парсит 'плечо 30', 'плечо на 120', 'локоть 90', 'base 45'.
    Возвращает (joint_en, angle, response) или None."""
    import re as _re
    aliases = sorted(JOINT_ALIASES.keys(), key=len, reverse=True)
    for alias in aliases:
        pattern = r"\b" + _re.escape(alias) + r"\s+(?:на\s+)?(-?\d{1,3})\b"
        m = _re.search(pattern, text_lower)
        if m:
            try:
                angle = int(m.group(1))
            except Exception:
                continue
            joint_en = JOINT_ALIASES[alias]
            lo, hi = JOINT_LIMITS_CORE[joint_en]
            if angle < lo or angle > hi:
                return (joint_en, None,
                        "Угол " + str(angle) + " вне диапазона для " + alias +
                        " (" + str(lo) + ".." + str(hi) + "), Сэр.")
            resp = "Установил " + alias + " на " + str(angle) + " градусов, Сэр."
            return (joint_en, angle, resp)
    return None


def _match_quick_command(text_lower: str):
    for cmd in QUICK_COMMANDS:
        if any(w in text_lower for w in cmd["keywords"]):
            return cmd["action"], cmd["response"]
    return None


# ============================================================
#  СЛУЖЕБНЫЕ КОМАНДЫ (status, help)
# ============================================================

STATUS_KEYWORDS = ["статус", "состояние", "как система", "что с системой"]
HELP_KEYWORDS = ["что умеешь", "помощь", "команды", "справка", "что можешь", "help"]
REMEMBER_KEYWORDS = ["запомни", "запомнить"]
RECALL_KEYWORDS = ["вспомни", "напомни", "что ты знаешь про"]


# ============================================================
#  ПАМЯТЬ
# ============================================================



# ============================================================
#  ИНИЦИАТИВА (фоновые фразы)
# ============================================================

INITIATIVE_PHRASES = [
    "Сэр, системы функционируют в штатном режиме.",
    "Сэр, ожидаю распоряжений. Латверия не дремлет.",
    "Сэр, все датчики в норме. Готов к работе.",
    "Сэр, зафиксировал стабильность параметров. Приказывайте.",
    "Сэр, работоспособность подтверждена. Жду задачи.",
    "Сэр, докладываю: роборука в готовности.",
    "Сэр, время течёт, а цели ждут. Каковы указания?",
    "Сэр, тишина — это тоже информация. Всё в порядке.",
    "Сэр, напоминаю о себе. Готов служить.",
    "Сэр, проверка связи успешна. Что прикажете?",
    "Сэр, империя не управляется сама собой. Жду решений.",
    "Сэр, если позволите — я бы предложил заняться делом.",
    "Сэр, наблюдение продолжается. Отклонений нет.",
    "Сэр, возможно, стоит что-то предпринять?",
    "Сэр, я в режиме ожидания. Все системы активны.",
    "Сэр, доложить о чём-либо?",
    "Сэр, время бездействия — потеря ресурсов.",
    "Сэр, у меня есть свободные вычислительные циклы. Используем их?",
    "Сэр, статус — стабильно. Курс — на Латверию.",
    "Сэр, если нужна помощь — я здесь.",
    "Сэр, фоновая активность низкая. Готов к работе.",
    "Сэр, разрешите продолжить выполнение задач?",
]


def _get_random_interval():
    """Случайный интервал между инициативами: 5-7 минут."""
    return random.randint(300, 420)


def _pick_initiative():
    """Случайная фраза (без повтора предыдущей)."""
    return random.choice(INITIATIVE_PHRASES)


class LongTermMemory:
    def __init__(self, path=MEMORY_FILE):
        self.path = path
        self.conversation = []
        self.objects = {}
        self.facts = {}
        self.load()

    def add_message(self, role, content):
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.conversation.append(msg)
        if len(self.conversation) > 500:
            self.conversation = self.conversation[-500:]
        self.save()

    def get_recent(self, count=6):
        return self.conversation[-count:] if self.conversation else []

    def remember_fact(self, key, value):
        self.facts[key] = value
        self.save()

    def recall_fact(self, key):
        return self.facts.get(key)

    def save(self):
        try:
            data = {
                "conversation": self.conversation,
                "objects": self.objects,
                "facts": self.facts
            }
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[MEMORY ERR] save: {e}")

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.conversation = data.get("conversation", [])
            self.objects = data.get("objects", {})
            self.facts = data.get("facts", {})
        except FileNotFoundError:
            self.save()
        except Exception as e:
            print(f"[MEMORY ERR] load: {e}")


class UserMemory:
    def __init__(self, path=USER_MEMORY_FILE):
        self.path = path
        self.favorites = {}
        self.facts = {}
        self.load()

    def set_fact(self, key, value):
        self.facts[key] = value
        self.save()

    def get_fact(self, key):
        return self.facts.get(key)

    def set_favorite(self, category, value):
        self.favorites[category] = value
        self.save()

    def get_favorite(self, category):
        return self.favorites.get(category)

    def learn_from_text(self, text_lower):
        learned = []
        m = re.search(r"мой любимый цвет[\s\-—:.,]+([а-яёa-z]+)", text_lower)
        if m:
            self.favorites["color"] = m.group(1)
            learned.append(f"цвет={m.group(1)}")
        m = re.search(r"мо[йя] любим[аяый]+\s+(фильм|книга|игра)\s*[\-—:.,]*\s*(.+)", text_lower)
        if m:
            val = m.group(2).strip()[:60]
            self.favorites[m.group(1)] = val
            learned.append(f"{m.group(1)}={val[:40]}")
        if learned:
            self.save()
        return learned

    def save(self):
        try:
            data = {
                "favorites": self.favorites,
                "facts": self.facts
            }
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[USER MEM ERR] save: {e}")

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.favorites = data.get("favorites", {})
            self.facts = data.get("facts", {})
        except FileNotFoundError:
            self.save()
        except Exception as e:
            print(f"[USER MEM ERR] load: {e}")


# ============================================================
#  ЯДРО
# ============================================================

# --- DNS-патч для OpenRouter (Termux не читает /etc/hosts из Python) ---
import socket as _socket_mod
_ORIG_GETADDRINFO = _socket_mod.getaddrinfo
_OPENROUTER_IPS = ["104.18.2.115", "104.18.3.115"]

def _patched_getaddrinfo(host, *args, **kwargs):
    if isinstance(host, str) and host.lower() == "openrouter.ai":
        for ip in _OPENROUTER_IPS:
            try:
                return _ORIG_GETADDRINFO(ip, *args, **kwargs)
            except Exception:
                continue
    return _ORIG_GETADDRINFO(host, *args, **kwargs)

_socket_mod.getaddrinfo = _patched_getaddrinfo
print("[GENESIS CORE] DNS-патч для openrouter.ai активирован.")
# --- конец патча ---



def _fix_names(text):
    """Убирает только выдуманные слова вселенной Marvel (не реальные страны)."""
    if not text:
        return text
    import re as _re
    # ТОЛЬКО выдуманные/ошибочные слова. Реальные страны (Латвия, Литва) не трогаем.
    patterns = [
        r"\bЛатвени[яиюей]*\b",    # Латвения
        r"\bЛатвини[яиюей]*\b",    # Латвиния
        r"\bЛатвери[яиюей]*\b",    # Латверия
        r"\bЛаверни[яиюей]*\b",    # Лаверния
    ]
    for p in patterns:
        text = _re.sub(p, "", text, flags=_re.IGNORECASE)
    # Чистим артефакты: двойные пробелы, " ,", " ."
    text = _re.sub(r"\s+", " ", text)
    text = text.replace(" ,", ",").replace(" .", ".")
    text = text.replace("правитель ,", "правитель,")
    text = text.replace("хозяин ,", "хозяин,")
    text = text.replace("повелитель ,", "повелитель,")
    return text.strip()


class GenesisCore:
    def __init__(self):
        self.api_key = API_KEY
        self.ready = self.api_key is not None
        self.dispatcher = None
        self.last_pose = {}
        self.long_mem = LongTermMemory()
        self.user_mem = UserMemory()
        self.last_initiative_time = time.time()
        self.next_initiative_interval = _get_random_interval()
        # Голос
        self.tts = TTSEngine() if TTS_AVAILABLE else None
        self.voice_enabled = False  # Голос отключён: termux-tts-speak не работает стабильно
        self.voice_web = False
        if self.voice_enabled:
            print("[GENESIS CORE] Голос подключён")

    def _speak(self, text: str):
        """Озвучивает текст (если голос включён)."""
        if not self.voice_enabled or not self.tts or not text:
            return
        # Если веб сам играет — не дублируем
        if getattr(self, "voice_web", False):
            return
        try:
            # Очистка от markdown и лишних пробелов
            clean = re.sub(r'[*_`#>]', '', text)
            clean = re.sub(r'\s+', ' ', clean).strip()
            # Обрезаем очень длинные ответы (TTS не для лекций)
            if len(clean) > 400:
                clean = clean[:400] + "..."
            if clean:
                self.tts.speak(clean)
        except Exception as e:
            print(f"[GENESIS CORE] TTS ошибка: {e}")
        print("[GENESIS CORE] Инициализация...")
        if self.ready:
            print(f"[GENESIS CORE] API-ключ загружен, модель: {MODELS[0]}")
        else:
            print("[GENESIS CORE] API-ключ не найден — режим оффлайн")
        print(f"[GENESIS CORE] История: {len(self.long_mem.conversation)} сообщений")

    def _wrap(self, initiative, response: str) -> str:
        """Добавляет фразу инициативы перед ответом, если есть."""
        if initiative:
            return initiative + "\n\n" + response
        return response

    def _execute_action(self, action: str):
        if self.dispatcher is None:
            return False
        try:
            json_str = '{"action": "' + action + '"}'
            self.dispatcher.execute_action(json_str)
            return True
        except Exception as e:
            print(f"[GENESIS CORE] Ошибка действия '{action}': {e}")
            return False

    def _check_initiative(self):
        """Возвращает фразу инициативы, если пора. Иначе None."""
        now = time.time()
        elapsed = now - self.last_initiative_time
        # Если бездействие дольше 15 минут — не спамим, сбрасываем
        if elapsed > 900:
            self.last_initiative_time = now
            self.next_initiative_interval = _get_random_interval()
            return None
        if elapsed >= self.next_initiative_interval:
            self.last_initiative_time = now
            self.next_initiative_interval = _get_random_interval()
            return _pick_initiative()
        return None

    def _cmd_status(self) -> str:
        lines = ["Отчёт о состоянии системы, Сэр:"]
        lines.append(f"— LLM: {'активна' if self.ready else 'оффлайн'}")
        if self.ready:
            lines.append(f"— Модель: {MODELS[0]}")
        lines.append(f"— История: {len(self.long_mem.conversation)} сообщений")
        lines.append(f"— Объектов в памяти: {len(self.long_mem.objects)}")
        lines.append(f"— Фактов о вас: {len(self.user_mem.facts) + len(self.user_mem.favorites)}")
        lines.append(f"— Роборука: {'подключена' if self.dispatcher else 'заглушка'}")
        return "\n".join(lines)

    def _cmd_help(self) -> str:
        lines = ["Мои возможности, Сэр:"]
        lines.append("— Движение: «домой», «схвати», «отпусти», «проснись»")
        lines.append("— Память: «запомни цвет — X», «мой любимый X — Y»")
        lines.append("— Информация: «статус», «что ты умеешь»")
        lines.append("— Разговор: любые вопросы на русском")
        lines.append("— Обращение: всегда «Сэр» или «Мистер»")
        return "\n".join(lines)

    def _cmd_remember(self, text: str) -> str:
        """«Запомни: ключ — значение» → сохраняет факт."""
        # Убираем слово "запомни" из начала
        cleaned = re.sub(r"^\s*запомни[ть]?\s*[:,-—]?\s*", "", text, flags=re.IGNORECASE).strip()
        # Ищем разделитель: "—", "-", ":", " это "
        m = re.match(r"(.+?)\s*(?:—|-|:|это)\s*(.+)", cleaned)
        if not m:
            return "Не понял, что запомнить, Сэр. Формат: «Запомни: ключ — значение»."
        key = m.group(1).strip().lower()
        value = m.group(2).strip()
        # Ограничения
        if len(key) > 40 or len(value) > 200:
            return "Слишком длинно для памяти, Сэр."
        self.long_mem.remember_fact(key, value)
        return f"Запомнил, Сэр. {key}: {value}."

    def _cmd_recall(self, text: str) -> str:
        """«Вспомни ключ» → возвращает факт."""
        cleaned = re.sub(r"^\s*(?:вспомни|напомни|что ты знаешь про|расскажи про)\s*[:,-—]?\s*", "", text, flags=re.IGNORECASE).strip()
        if not cleaned:
            return "Что именно вспомнить, Сэр?"
        key = cleaned.lower().rstrip("?.!").strip()
        value = self.long_mem.recall_fact(key)
        if value is None:
            # Пробуем частичное совпадение
            for k, v in self.long_mem.facts.items():
                if key in k or k in key:
                    return f"Сэр, {k}: {v}."
            return f"Не сохранил информации о «{key}», Сэр."
        return f"Сэр, {key}: {value}."

    def ask(self, text: str) -> str:
        if not text or not text.strip():
            return "..."

        t_lower = text.lower()
        self.user_mem.learn_from_text(t_lower)
        self.long_mem.add_message("user", text)

        # Фоновый комментарий (если пора)
        initiative = ""  # отключено: не вставляем фразы в обычные ответы

        # 1.6. Точные команды суставов: "плечо 30", "локоть на 120"
        parsed = _parse_joint_command(t_lower)
        if parsed:
            joint, angle, resp = parsed
            if angle is not None:
                self.last_pose = {joint: angle}
            self.long_mem.add_message("assistant", resp)
            self._speak(resp)
            return self._wrap(initiative, resp)

        # 1. Служебные команды
        if any(w in t_lower for w in STATUS_KEYWORDS):
            resp = self._cmd_status()
            self.long_mem.add_message("assistant", resp)
            return self._wrap(initiative, resp)
        if any(w in t_lower for w in HELP_KEYWORDS):
            resp = self._cmd_help()
            self.long_mem.add_message("assistant", resp)
            return self._wrap(initiative, resp)

        # 1.3.5. Телефон (Termux:API)
        import urllib.request as _urq_phone
        import json as _json_phone

        def _phone_api(cmd_name):
            import subprocess as _sp_phone
            import json as _jp
            try:
                if cmd_name == "battery":
                    import os as _osb
                    import time as _tb
                    _cache_path = _osb.path.expanduser("~/battery_cache.json")
                    _d = None
                    if _osb.path.exists(_cache_path):
                        try:
                            with open(_cache_path, "r", encoding="utf-8") as _f:
                                _cache = _jp.load(_f)
                            if _tb.time() - _cache.get("ts", 0) < 120:
                                _d = _cache.get("data")
                        except Exception:
                            _d = None
                    if _d is None:
                        r = _sp_phone.run(["termux-battery-status"], capture_output=True, text=True, timeout=25)
                        if r.returncode != 0:
                            return {"ok": False, "error": r.stderr.strip()}
                        _d = _jp.loads(r.stdout)
                    d = _d
                    plugged = d.get("plugged", "UNPLUGGED")
                    if plugged == "UNPLUGGED":
                        status = "не на зарядке"
                    elif plugged == "PLUGGED_AC":
                        status = "заряжается от сети"
                    elif plugged == "PLUGGED_USB":
                        status = "заряжается от USB"
                    elif plugged == "PLUGGED_WIRELESS":
                        status = "беспроводная зарядка"
                    else:
                        status = "заряжается"
                    return {"ok": True, "reply": "Батарея: " + str(d.get("percentage")) + "%, " + status + ", температура " + str(d.get("temperature")) + "\u00b0C."}
                if cmd_name == "volume":
                    import os as _osv
                    import time as _tv
                    _cache_v = _osv.path.expanduser("~/volume_cache.json")
                    _data_v = None
                    if _osv.path.exists(_cache_v):
                        try:
                            with open(_cache_v, "r", encoding="utf-8") as _fv:
                                _cache_vd = _jp.load(_fv)
                            if _tv.time() - _cache_vd.get("ts", 0) < 120:
                                _data_v = _cache_vd.get("data")
                        except Exception:
                            _data_v = None
                    if _data_v is None:
                        r = _sp_phone.run(["termux-volume"], capture_output=True, text=True, timeout=20)
                        if r.returncode != 0:
                            return {"ok": False, "error": r.stderr.strip()}
                        _data_v = _jp.loads(r.stdout)
                    parts = []
                    for s in _data_v:
                        name = s.get("stream")
                        if name in ("music", "ring", "notification"):
                            parts.append(name + ": " + str(s.get("volume")) + "/" + str(s.get("max_volume")))
                    return {"ok": True, "reply": "Громкость \u2014 " + " \u00b7 ".join(parts)}
                if cmd_name.startswith("volume_set:"):
                    parts = cmd_name.split(":")
                    if len(parts) == 3:
                        stream, level = parts[1], parts[2]
                        r = _sp_phone.run(["termux-volume", stream, level], capture_output=True, text=True, timeout=10)
                        if r.returncode != 0:
                            return {"ok": False, "error": r.stderr.strip()}
                        return {"ok": True, "reply": "Громкость " + stream + " = " + level + ", Сэр."}
                if cmd_name.startswith("open_app:"):
                    app_name = cmd_name.split(":", 1)[1]
                    import urllib.request as _urq_open
                    import json as _jo
                    try:
                        req_o = _urq_open.Request(
                            "http://127.0.0.1:5000/api/phone/open",
                            data=_jo.dumps({"name": app_name}).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        with _urq_open.urlopen(req_o, timeout=10) as _ro:
                            return _jo.loads(_ro.read().decode("utf-8"))
                    except Exception as _e:
                        return {"ok": False, "error": str(_e)}
                return {"ok": False, "error": "unknown"}
            except Exception as _e:
                return {"ok": False, "error": str(_e)}

        _pc = None
        _tl = text.lower().strip()
        import re as _re_pc
        if _tl in ("батарея", "заряд", "зарядка", "уровень заряда"):
            _pc = "battery"
        elif _tl in ("громкость", "звук"):
            _pc = "volume"
        else:
            _m = _re_pc.match(r"^(?:громкость|звук)\s+(music|ring|notification|alarm|system)\s+(\d{1,2})$", _tl)
            if _m:
                _pc = "volume_set:" + _m.group(1) + ":" + _m.group(2)
            else:
                _m_open = _re_pc.match(r"^(?:открой|запусти|open|start)\s+(.+)$", _tl)
                if _m_open:
                    _pc = "open_app:" + _m_open.group(1).strip()

        if _pc:
            _r = _phone_api(_pc)
            if _r.get("ok"):
                resp = _r.get("reply") or "Готово."
            else:
                resp = "Сэр, не удалось: " + str(_r.get("error"))
            self.long_mem.add_message("assistant", resp)
            self._speak(resp)
            return self._wrap(initiative, resp)

        # 1.4. Заметки / Напоминания / Дневник
        import re as _re_notes
        import os as _os_notes
        import json as _json_notes
        import time as _time_notes

        _NOTES_FILE = _os_notes.path.expanduser("~/genesis_notes.json")

        def _notes_load_local():
            if not _os_notes.path.exists(_NOTES_FILE):
                return {"notes": [], "reminders": [], "diary": []}
            try:
                with open(_NOTES_FILE, "r", encoding="utf-8") as _f:
                    _d = _json_notes.load(_f)
                for _k in ("notes", "reminders", "diary"):
                    _d.setdefault(_k, [])
                return _d
            except Exception:
                return {"notes": [], "reminders": [], "diary": []}

        def _notes_save_local(_d):
            with open(_NOTES_FILE, "w", encoding="utf-8") as _f:
                _json_notes.dump(_d, _f, ensure_ascii=False, indent=2)

        def _notes_next_id_local(_items):
            return max((_it.get("id", 0) for _it in _items), default=0) + 1

        _note_cmd = None
        _note_type = None
        _note_content = ""
        _note_when = ""

        _m = _re_notes.match(r'^заметка\s*[:\-]\s*(.+)$', text, _re_notes.I)
        if _m:
            _note_cmd, _note_type, _note_content = "add", "notes", _m.group(1).strip()
        if _note_cmd is None:
            _m = _re_notes.match(r'^запомни\s*[:\-]\s*(.+)$', text, _re_notes.I)
            if _m:
                _note_cmd, _note_type, _note_content = "add", "notes", _m.group(1).strip()
        if _note_cmd is None:
            _m = _re_notes.match(r'^запиши\s+в\s+дневник\s*[:\-]?\s*(.+)$', text, _re_notes.I)
            if _m:
                _note_cmd, _note_type, _note_content = "add", "diary", _m.group(1).strip()
        if _note_cmd is None:
            _m = _re_notes.match(r'^дневник\s*[:\-]\s*(.+)$', text, _re_notes.I)
            if _m:
                _note_cmd, _note_type, _note_content = "add", "diary", _m.group(1).strip()
        if _note_cmd is None:
            _m = _re_notes.match(r'^напоминание\s*[:\-]\s*(.+)$', text, _re_notes.I)
            if _m:
                _note_cmd, _note_type, _note_content = "add", "reminders", _m.group(1).strip()
        if _note_cmd is None:
            _m = _re_notes.match(r'^напомни\s+(.+?)(?:\s+в\s+(.+))?$', text, _re_notes.I)
            if _m:
                _note_cmd, _note_type, _note_content = "add", "reminders", _m.group(1).strip()
                if _m.lastindex and _m.lastindex >= 2 and _m.group(2):
                    _note_when = _m.group(2).strip()

        if _note_cmd == "add" and _note_content:
            _store = _notes_load_local()
            _item = {
                "id": _notes_next_id_local(_store[_note_type]),
                "text": _note_content,
                "ts": _time_notes.strftime("%Y-%m-%d %H:%M:%S"),
            }
            if _note_type == "reminders":
                _item["when"] = _note_when
            if _note_type == "diary":
                _item["date"] = _time_notes.strftime("%Y-%m-%d")
            _store[_note_type].append(_item)
            _notes_save_local(_store)

            _label = {"notes": "Заметки", "reminders": "Напоминания", "diary": "Дневник"}[_note_type]
            _extra = ""
            if _note_type == "reminders" and _note_when:
                _extra = " (" + _note_when + ")"
            resp = "Добавил в " + _label + ", Сэр: " + _note_content + _extra
            self.long_mem.add_message("assistant", resp)
            self._speak(resp)
            return self._wrap(initiative, resp)

        # 1.5. Память (remember)
        if any(w in t_lower for w in REMEMBER_KEYWORDS):
            resp = self._cmd_remember(text)
            self.long_mem.add_message("assistant", resp)
            self._speak(resp)
            return self._wrap(initiative, resp)
        
        # recall — только если ключ ЕСТЬ в памяти
        if any(w in t_lower for w in RECALL_KEYWORDS):
            resp = self._cmd_recall(text)
            # Если recall реально нашёл что-то — возвращаем
            # Иначе — падаем в LLM (не факт что знаем)
            if "Не сохранил информации" not in resp:
                self.long_mem.add_message("assistant", resp)
                self._speak(resp)
                return self._wrap(initiative, resp)
            # Если не нашли — идём дальше (LLM ответит)

        # 1.6. Точные команды суставов: "плечо 30", "локоть на 120"
        parsed = _parse_joint_command(t_lower)
        if parsed:
            joint, angle, resp = parsed
            if angle is not None:
                self.last_pose = {joint: angle}
            self.long_mem.add_message("assistant", resp)
            self._speak(resp)
            return self._wrap(initiative, resp)

        # 2. Быстрые команды робота
        quick = _match_quick_command(t_lower)
        if quick:
            action, response = quick
            self._execute_action(action)
            self.long_mem.add_message("assistant", response)
            self._speak(response)
            return self._wrap(initiative, response)

        # 3. LLM
        if self.ready:
            response = self._ask_ai(text)
            if response:
                clean_text, action_json = self._parse_response(response)
                if action_json and self.dispatcher:
                    try:
                        self.dispatcher.execute_action(action_json)
                    except Exception as e:
                        print(f"[GENESIS CORE] Ошибка действия из LLM: {e}")
                self.long_mem.add_message("assistant", clean_text)
                self._speak(clean_text)
                return self._wrap(initiative, clean_text)

        # 4. Fallback
        fallback = self._local_answer(text)
        self.long_mem.add_message("assistant", fallback)
        self._speak(fallback)
        return self._wrap(initiative, fallback)

    def _parse_response(self, text: str):
        if not text:
            return "", None
        pattern = r'\{[^{}]*"action"[^{}]*\}'
        matches = re.findall(pattern, text)
        if not matches:
            clean = text.strip()
        else:
            action_json = matches[-1]
            clean = text.replace(action_json, "").strip()
            clean = re.sub(r'\n{3,}', '\n\n', clean)
        clean = re.sub(r'[\U0001F300-\U0001FAFF]+\s*$', '', clean).strip()
        return clean, (matches[-1] if matches else None)

    def _ask_ai(self, text: str) -> str:
        recent = self.long_mem.get_recent(6)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in recent[:-1]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": text})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        ctx = ssl._create_unverified_context()

        for model in MODELS:
            for attempt in range(1, 3):
                data = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 500
                }
                try:
                    req = urllib.request.Request(
                        API_URL,
                        data=json.dumps(data).encode("utf-8"),
                        headers=headers,
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                        result = json.loads(resp.read().decode("utf-8"))
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if not content:
                            continue
                        return _fix_names(self._clean_reasoning(content.strip()))
                except urllib.error.HTTPError as e:
                    print(f"[GENESIS CORE] {model}: HTTP {e.code}")
                    if e.code == 429:
                        time.sleep(5)
                        break
                    else:
                        break
                except Exception as e:
                    print(f"[GENESIS CORE] {model} попытка {attempt}/2: {e}")
                    if attempt < 2:
                        time.sleep(1)
                    else:
                        break
        return None

    def _clean_reasoning(self, content: str) -> str:
        markers = [
            "thinking process", "Analyze User", "Identify",
            "Determine Action", "Here's a thinking", "**Analyze", "**Identify"
        ]
        if any(m in content for m in markers):
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if paragraphs:
                content = paragraphs[-1]
        return content.lstrip("-\n ").strip()

    def _local_answer(self, text: str) -> str:
        t = text.lower()
        if "ты кто" in t or "кто ты" in t:
            return "Я — KAIROS. Ваш помощник в робототехнике, Сэр."
        if "привет" in t or "здравствуй" in t:
            return "Приветствую, Сэр. Системы в норме."
        return "Запрос принят, Сэр. LLM недоступна."


# ============================================================
#  ТЕСТ
# ============================================================

def main():
    print("=" * 50)
    print("  GENESIS CORE — status + help")
    print("=" * 50)
    core = GenesisCore()
    print("-" * 50)
    tests = ["Статус", "Что ты умеешь?", "Домой", "Как дела?"]
    for t in tests:
        print(f">>> {t}")
        print(core.ask(t))
        print("-" * 50)


if __name__ == "__main__":
    main()
