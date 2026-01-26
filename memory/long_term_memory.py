from typing import Dict, List, Optional
from pathlib import Path
import json
import aiofiles
from datetime import datetime
import logging

from config import MAX_FACTS_PER_USER, ENABLE_LONG_TERM_MEMORY

logger = logging.getLogger(__name__)


class LongTermMemory:
    """Долгосрочная память - запоминание фактов о пользователе"""

    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.memory_file = self.storage_dir / "long_term_memory.json"
        self._cache: Dict[int, Dict] = {}
        self.enabled = ENABLE_LONG_TERM_MEMORY

    async def _load_all_memories(self) -> Dict[str, Dict]:
        """Загружает всю долгосрочную память"""
        if not self.memory_file.exists():
            return {}

        try:
            async with aiofiles.open(self.memory_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка загрузки долгосрочной памяти: {e}")
            return {}

    async def _save_all_memories(self, data: Dict[str, Dict]):
        """Сохраняет всю долгосрочную память"""
        try:
            async with aiofiles.open(self.memory_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Ошибка сохранения долгосрочной памяти: {e}")

    async def get_memory(self, user_id: int) -> Dict:
        """Получает память о пользователе"""
        if not self.enabled:
            return self._get_empty_memory()

        if user_id in self._cache:
            return self._cache[user_id]

        all_memories = await self._load_all_memories()
        memory = all_memories.get(str(user_id), self._get_empty_memory())

        self._cache[user_id] = memory
        return memory

    def _get_empty_memory(self) -> Dict:
        """Возвращает пустую структуру памяти"""
        return {
            "name": None,
            "facts": [],
            "interests": [],
            "favorite_anime": [],
            "favorite_games": [],
            "birthday": None,
            "notes": []
        }

    async def add_fact(self, user_id: int, fact: str):
        """Добавляет факт о пользователе"""
        if not self.enabled:
            return

        all_memories = await self._load_all_memories()

        if str(user_id) not in all_memories:
            all_memories[str(user_id)] = self._get_empty_memory()

        user_memory = all_memories[str(user_id)]

        # Добавляем факт с timestamp
        user_memory["facts"].append({
            "text": fact,
            "timestamp": datetime.now().isoformat()
        })

        # Ограничиваем количество фактов
        if len(user_memory["facts"]) > MAX_FACTS_PER_USER:
            user_memory["facts"] = user_memory["facts"][-MAX_FACTS_PER_USER:]

        await self._save_all_memories(all_memories)
        self._cache[user_id] = user_memory

        logger.info(f"Добавлен факт для пользователя {user_id}: {fact}")

    async def set_name(self, user_id: int, name: str):
        """Устанавливает имя пользователя"""
        if not self.enabled:
            return

        all_memories = await self._load_all_memories()

        if str(user_id) not in all_memories:
            all_memories[str(user_id)] = self._get_empty_memory()

        all_memories[str(user_id)]["name"] = name

        await self._save_all_memories(all_memories)
        self._cache[user_id] = all_memories[str(user_id)]

        logger.info(f"Установлено имя для {user_id}: {name}")

    async def get_context_string(self, user_id: int) -> str:
        """Возвращает строку с контекстом для промпта"""
        memory = await self.get_memory(user_id)

        context_parts = []

        if memory["name"]:
            context_parts.append(f"Имя собеседника: {memory['name']}")

        if memory["facts"]:
            recent_facts = [f["text"] for f in memory["facts"][-5:]]
            context_parts.append(f"Факты о нём: {', '.join(recent_facts)}")

        if memory["interests"]:
            context_parts.append(f"Интересы: {', '.join(memory['interests'])}")

        if memory["favorite_anime"]:
            context_parts.append(f"Любимое аниме: {', '.join(memory['favorite_anime'])}")

        if memory["favorite_games"]:
            context_parts.append(f"Любимые игры: {', '.join(memory['favorite_games'])}")

        if not context_parts:
            return ""

        return "\n\n📝 ЧТО ТЫ ЗНАЕШЬ О СОБЕСЕДНИКЕ:\n" + "\n".join(context_parts)