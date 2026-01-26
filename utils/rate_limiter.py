from datetime import datetime, timedelta
from typing import Dict
import logging

from config import MAX_MESSAGES_PER_MINUTE, MAX_MESSAGES_PER_DAY, COOLDOWN_SECONDS

logger = logging.getLogger(__name__)


class RateLimiter:
    """Защита от спама - ограничение частоты сообщений"""

    def __init__(self):
        self._user_timestamps: Dict[int, list] = {}
        self._last_message_time: Dict[int, datetime] = {}

    def is_allowed(self, user_id: int) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь отправить сообщение

        Returns:
            (allowed, reason) - разрешено ли и причина отказа
        """
        now = datetime.now()

        # 1. Проверка cooldown (задержка между сообщениями)
        if user_id in self._last_message_time:
            time_since_last = (now - self._last_message_time[user_id]).total_seconds()
            if time_since_last < COOLDOWN_SECONDS:
                remaining = COOLDOWN_SECONDS - time_since_last
                return False, f"Подожди {remaining:.1f} секунд перед следующим сообщением"

        # 2. Получаем историю сообщений пользователя
        if user_id not in self._user_timestamps:
            self._user_timestamps[user_id] = []

        timestamps = self._user_timestamps[user_id]

        # 3. Очищаем старые timestamps
        one_minute_ago = now - timedelta(minutes=1)
        one_day_ago = now - timedelta(days=1)

        timestamps = [ts for ts in timestamps if ts > one_day_ago]
        self._user_timestamps[user_id] = timestamps

        # 4. Проверка лимита в минуту
        recent_messages = [ts for ts in timestamps if ts > one_minute_ago]
        if len(recent_messages) >= MAX_MESSAGES_PER_MINUTE:
            return False, f"Слишком много сообщений! Максимум {MAX_MESSAGES_PER_MINUTE} в минуту"

        # 5. Проверка лимита в день
        if len(timestamps) >= MAX_MESSAGES_PER_DAY:
            return False, f"Достигнут дневной лимит ({MAX_MESSAGES_PER_DAY} сообщений)"

        return True, ""

    def record_message(self, user_id: int):
        """Записывает время сообщения"""
        now = datetime.now()

        if user_id not in self._user_timestamps:
            self._user_timestamps[user_id] = []

        self._user_timestamps[user_id].append(now)
        self._last_message_time[user_id] = now

        logger.debug(f"Recorded message from user {user_id}")

    def reset_user(self, user_id: int):
        """Сбрасывает лимиты для пользователя (для админов)"""
        if user_id in self._user_timestamps:
            del self._user_timestamps[user_id]
        if user_id in self._last_message_time:
            del self._last_message_time[user_id]

        logger.info(f"Reset rate limits for user {user_id}")