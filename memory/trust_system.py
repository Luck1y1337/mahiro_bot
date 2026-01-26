from typing import Dict
import json
from pathlib import Path
import aiofiles
import logging

from config import TRUST_INCREMENT, MAX_TRUST

logger = logging.getLogger(__name__)


class TrustSystem:
    """Система доверия между пользователем и Махиро"""

    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.trust_file = self.storage_dir / "trust_levels.json"
        self._cache: Dict[int, float] = {}

    async def _load_all_trust(self) -> Dict[str, float]:
        """Загружает все уровни доверия"""
        if not self.trust_file.exists():
            return {}

        try:
            async with aiofiles.open(self.trust_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка загрузки trust levels: {e}")
            return {}

    async def _save_all_trust(self, data: Dict[str, float]):
        """Сохраняет все уровни доверия"""
        try:
            async with aiofiles.open(self.trust_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Ошибка сохранения trust levels: {e}")

    async def get_trust(self, user_id: int) -> float:
        """Получает уровень доверия пользователя"""
        if user_id in self._cache:
            return self._cache[user_id]

        all_trust = await self._load_all_trust()
        trust = all_trust.get(str(user_id), 0.0)
        self._cache[user_id] = trust
        return trust

    async def increment_trust(self, user_id: int):
        """Увеличивает доверие пользователю"""
        current_trust = await self.get_trust(user_id)
        new_trust = min(current_trust + TRUST_INCREMENT, MAX_TRUST)

        all_trust = await self._load_all_trust()
        all_trust[str(user_id)] = new_trust
        await self._save_all_trust(all_trust)

        self._cache[user_id] = new_trust
        logger.info(f"Trust для пользователя {user_id}: {new_trust:.2f}")