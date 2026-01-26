import random
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import json
import aiofiles
import logging

logger = logging.getLogger(__name__)


class MoodSystem:
    """
    Динамическая система настроения Махиро

    Настроения:
    - обычное (нейтральное)
    - счастливая
    - раздражённая
    - усталая
    - сонная
    - взволнованная
    - грустная
    """

    MOODS = [
        "обычное",
        "счастливая",
        "раздражённая",
        "усталая",
        "сонная",
        "взволнованная",
        "грустная"
    ]

    # Вероятность случайной смены настроения (5%)
    RANDOM_MOOD_CHANGE_CHANCE = 0.05

    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.mood_file = self.storage_dir / "moods.json"
        self._cache: Dict[int, Dict] = {}

    async def _load_all_moods(self) -> Dict[str, Dict]:
        """Загружает все настроения пользователей"""
        if not self.mood_file.exists():
            return {}

        try:
            async with aiofiles.open(self.mood_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка загрузки настроений: {e}")
            return {}

    async def _save_all_moods(self, data: Dict[str, Dict]):
        """Сохраняет все настроения"""
        try:
            async with aiofiles.open(self.mood_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Ошибка сохранения настроений: {e}")

    async def get_mood(self, user_id: int) -> str:
        """Получает текущее настроение для пользователя"""
        if user_id in self._cache:
            return self._cache[user_id].get("mood", "обычное")

        all_moods = await self._load_all_moods()
        user_data = all_moods.get(str(user_id), {"mood": "обычное", "timestamp": datetime.now().isoformat()})

        # Кэшируем
        self._cache[user_id] = user_data

        return user_data.get("mood", "обычное")

    async def set_mood(self, user_id: int, mood: str):
        """Устанавливает настроение для пользователя"""
        if mood not in self.MOODS:
            logger.warning(f"Неизвестное настроение: {mood}")
            mood = "обычное"

        all_moods = await self._load_all_moods()
        all_moods[str(user_id)] = {
            "mood": mood,
            "timestamp": datetime.now().isoformat()
        }
        await self._save_all_moods(all_moods)

        self._cache[user_id] = all_moods[str(user_id)]
        logger.info(f"Настроение для {user_id}: {mood}")

    async def calculate_mood(
            self,
            user_id: int,
            message_text: str,
            time_of_day: str,
            trust_level: float,
            message_count_today: int = 0
    ) -> str:
        """
        Вычисляет настроение на основе контекста

        Args:
            user_id: ID пользователя
            message_text: текст сообщения
            time_of_day: время суток
            trust_level: уровень доверия
            message_count_today: сколько сообщений сегодня от этого пользователя

        Returns:
            Настроение
        """
        current_mood = await self.get_mood(user_id)

        # 1. Базовое настроение от времени суток
        base_mood = self._get_time_based_mood(time_of_day)

        # 2. Анализ сообщения пользователя
        message_mood = self._analyze_message(message_text, trust_level)

        # 3. Проверка на спам
        if message_count_today > 30:
            return "раздражённая"
        elif message_count_today > 50:
            return "усталая"

        # 4. Случайная смена настроения (редко)
        if random.random() < self.RANDOM_MOOD_CHANGE_CHANCE:
            new_mood = random.choice(self.MOODS)
            logger.info(f"Случайная смена настроения на: {new_mood}")
            await self.set_mood(user_id, new_mood)
            return new_mood

        # 5. Приоритет: сообщение > текущее > базовое
        if message_mood:
            final_mood = message_mood
        elif current_mood != "обычное":
            # Сохраняем текущее настроение, если оно не дефолтное
            final_mood = current_mood
        else:
            final_mood = base_mood

        # Сохраняем новое настроение
        if final_mood != current_mood:
            await self.set_mood(user_id, final_mood)

        return final_mood

    def _get_time_based_mood(self, time_of_day: str) -> str:
        """Определяет базовое настроение от времени суток"""
        mood_map = {
            "утро": random.choice(["сонная", "усталая", "обычное"]),
            "день": "обычное",
            "вечер": random.choice(["обычное", "счастливая"]),
            "ночь": random.choice(["сонная", "взволнованная", "обычное"])
        }
        return mood_map.get(time_of_day, "обычное")

    def _analyze_message(self, text: str, trust_level: float) -> Optional[str]:
        """
        Анализирует сообщение и определяет, нужно ли сменить настроение

        Returns:
            Новое настроение или None (не менять)
        """
        text_lower = text.lower()

        # Позитивные триггеры
        positive_triggers = [
            "люблю", "нравишься", "классная", "милая", "красивая",
            "хорошая", "умная", "крутая", "супер", "офигенная"
        ]

        # Негативные триггеры
        negative_triggers = [
            "тупая", "глупая", "дура", "идиот", "плохая",
            "отстань", "заткнись", "достала"
        ]

        # Грустные триггеры
        sad_triggers = [
            "грустно", "плохо", "печально", "одиноко", "скучно"
        ]

        # Проверка на комплименты (делают счастливой)
        if any(trigger in text_lower for trigger in positive_triggers):
            if trust_level > 0.3:  # только если доверие есть
                return "счастливая"

        # Проверка на грубость (раздражает)
        if any(trigger in text_lower for trigger in negative_triggers):
            return "раздражённая"

        # Проверка на грусть у пользователя (сочувствие)
        if any(trigger in text_lower for trigger in sad_triggers):
            if trust_level > 0.5:
                return "грустная"

        # Проверка на спам (короткие повторяющиеся сообщения)
        if len(text.strip()) < 3:
            return "раздражённая"

        # Проверка на длинные сообщения (взволнованность)
        if len(text) > 500:
            return "взволнованная"

        return None  # не менять настроение


class MessageCounter:
    """Счётчик сообщений для отслеживания спама"""

    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.counter_file = self.storage_dir / "message_counters.json"
        self._cache: Dict[str, int] = {}

    async def _load_counters(self) -> Dict[str, int]:
        """Загружает счётчики"""
        if not self.counter_file.exists():
            return {}

        try:
            async with aiofiles.open(self.counter_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка загрузки счётчиков: {e}")
            return {}

    async def _save_counters(self, data: Dict[str, int]):
        """Сохраняет счётчики"""
        try:
            async with aiofiles.open(self.counter_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Ошибка сохранения счётчиков: {e}")

    def _get_today_key(self, user_id: int) -> str:
        """Генерирует ключ для сегодняшнего дня"""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{user_id}_{today}"

    async def increment(self, user_id: int) -> int:
        """Увеличивает счётчик сообщений на сегодня"""
        key = self._get_today_key(user_id)

        counters = await self._load_counters()
        current = counters.get(key, 0)
        new_count = current + 1
        counters[key] = new_count

        await self._save_counters(counters)
        self._cache[key] = new_count

        return new_count

    async def get_count(self, user_id: int) -> int:
        """Получает количество сообщений сегодня"""
        key = self._get_today_key(user_id)

        if key in self._cache:
            return self._cache[key]

        counters = await self._load_counters()
        count = counters.get(key, 0)
        self._cache[key] = count

        return count