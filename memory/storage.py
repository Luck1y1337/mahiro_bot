from typing import Dict, List
import json
import aiofiles
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MemoryStorage:
    """Хранилище истории диалогов пользователей"""

    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def _get_user_file(self, user_id: int) -> Path:
        """Путь к файлу истории пользователя"""
        return self.storage_dir / f"user_{user_id}.json"

    async def load_history(self, user_id: int) -> List[Dict[str, str]]:
        """Загружает историю пользователя"""
        file_path = self._get_user_file(user_id)

        if not file_path.exists():
            return []

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
                return data.get("history", [])
        except Exception as e:
            logger.error(f"Ошибка загрузки истории для {user_id}: {e}")
            return []

    async def save_history(self, user_id: int, history: List[Dict[str, str]]):
        """Сохраняет историю пользователя"""
        file_path = self._get_user_file(user_id)

        try:
            data = {"history": history}
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Ошибка сохранения истории для {user_id}: {e}")

    async def add_message(self, user_id: int, role: str, content: str, max_messages: int = 20):
        """
        Добавляет сообщение в историю

        Args:
            user_id: ID пользователя
            role: "user" или "assistant"
            content: текст сообщения
            max_messages: максимальное количество сообщений в истории
        """
        history = await self.load_history(user_id)
        history.append({"role": role, "content": content})

        # Ограничиваем размер истории
        if len(history) > max_messages:
            history = history[-max_messages:]

        await self.save_history(user_id, history)