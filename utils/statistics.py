from pathlib import Path
import json
import aiofiles
from datetime import datetime
from typing import Dict
import logging

from config import ENABLE_STATISTICS

logger = logging.getLogger(__name__)


class Statistics:
    """Сбор и хранение статистики работы бота"""

    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.stats_file = self.storage_dir / "statistics.json"
        self.enabled = ENABLE_STATISTICS
        self._cache = None

    async def _load_stats(self) -> Dict:
        """Загружает статистику"""
        if not self.stats_file.exists():
            return self._get_default_stats()

        try:
            async with aiofiles.open(self.stats_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики: {e}")
            return self._get_default_stats()

    async def _save_stats(self, stats: Dict):
        """Сохраняет статистику"""
        try:
            async with aiofiles.open(self.stats_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(stats, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {e}")

    def _get_default_stats(self) -> Dict:
        """Возвращает дефолтную структуру статистики"""
        return {
            "total_messages": 0,
            "total_users": 0,
            "messages_by_mood": {
                "обычное": 0,
                "счастливая": 0,
                "раздражённая": 0,
                "усталая": 0,
                "сонная": 0,
                "взволнованная": 0,
                "грустная": 0
            },
            "triggers_activated": {},
            "images_sent": 0,
            "errors": 0,
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }

    async def increment_messages(self, mood: str = None):
        """Увеличивает счётчик сообщений"""
        if not self.enabled:
            return

        stats = await self._load_stats()
        stats["total_messages"] += 1

        if mood and mood in stats["messages_by_mood"]:
            stats["messages_by_mood"][mood] += 1

        stats["last_updated"] = datetime.now().isoformat()
        await self._save_stats(stats)

    async def add_user(self):
        """Добавляет нового пользователя"""
        if not self.enabled:
            return

        stats = await self._load_stats()
        stats["total_users"] += 1
        stats["last_updated"] = datetime.now().isoformat()
        await self._save_stats(stats)

    async def record_trigger(self, trigger_name: str):
        """Записывает активацию триггера"""
        if not self.enabled:
            return

        stats = await self._load_stats()

        if trigger_name not in stats["triggers_activated"]:
            stats["triggers_activated"][trigger_name] = 0

        stats["triggers_activated"][trigger_name] += 1
        stats["last_updated"] = datetime.now().isoformat()
        await self._save_stats(stats)

    async def increment_images(self):
        """Увеличивает счётчик отправленных картинок"""
        if not self.enabled:
            return

        stats = await self._load_stats()
        stats["images_sent"] += 1
        stats["last_updated"] = datetime.now().isoformat()
        await self._save_stats(stats)

    async def increment_errors(self):
        """Увеличивает счётчик ошибок"""
        if not self.enabled:
            return

        stats = await self._load_stats()
        stats["errors"] += 1
        stats["last_updated"] = datetime.now().isoformat()
        await self._save_stats(stats)

    async def get_stats(self) -> Dict:
        """Получает текущую статистику"""
        return await self._load_stats()

    async def format_stats(self) -> str:
        """Форматирует статистику для отображения"""
        stats = await self._load_stats()

        start_time = datetime.fromisoformat(stats["start_time"])
        uptime = datetime.now() - start_time
        uptime_str = f"{uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м"

        text = f"""📊 **Статистика бота Махиро**

⏱ Время работы: {uptime_str}
👥 Всего пользователей: {stats['total_users']}
💬 Всего сообщений: {stats['total_messages']}
🖼 Отправлено картинок: {stats['images_sent']}
❌ Ошибок: {stats['errors']}

**По настроениям:**
"""

        for mood, count in stats["messages_by_mood"].items():
            if count > 0:
                text += f"  • {mood}: {count}\n"

        if stats["triggers_activated"]:
            text += "\n**Топ триггеров:**\n"
            sorted_triggers = sorted(
                stats["triggers_activated"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            for trigger, count in sorted_triggers:
                text += f"  • {trigger}: {count}\n"

        return text