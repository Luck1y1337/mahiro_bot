from pathlib import Path
import json
import aiofiles
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class UserTracker:
    """
    Отслеживание всех пользователей, которые пытались использовать бота
    """

    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.users_file = self.storage_dir / "users_tracker.json"
        self._cache: Dict[int, Dict] = {}

    async def _load_users(self) -> Dict[str, Dict]:
        """Загружает всех пользователей"""
        if not self.users_file.exists():
            return {}

        try:
            async with aiofiles.open(self.users_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Ошибка загрузки user tracker: {e}")
            return {}

    async def _save_users(self, data: Dict[str, Dict]):
        """Сохраняет всех пользователей"""
        try:
            async with aiofiles.open(self.users_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Ошибка сохранения user tracker: {e}")

    async def track_user(self, user_id: int, username: str = None, first_name: str = None,
                         last_name: str = None, had_access: bool = True):
        """
        Отслеживает пользователя

        Args:
            user_id: ID пользователя
            username: username в Telegram
            first_name: имя
            last_name: фамилия
            had_access: был ли доступ разрешён
        """
        users = await self._load_users()

        user_key = str(user_id)
        now = datetime.now().isoformat()

        if user_key in users:
            # Обновляем существующего
            users[user_key]["last_seen"] = now
            users[user_key]["message_count"] = users[user_key].get("message_count", 0) + 1

            if had_access:
                users[user_key]["successful_messages"] = users[user_key].get("successful_messages", 0) + 1
            else:
                users[user_key]["blocked_messages"] = users[user_key].get("blocked_messages", 0) + 1

            # Обновляем имя/username если изменились
            if username:
                users[user_key]["username"] = username
            if first_name:
                users[user_key]["first_name"] = first_name
            if last_name:
                users[user_key]["last_name"] = last_name
        else:
            # Добавляем нового
            users[user_key] = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "first_seen": now,
                "last_seen": now,
                "message_count": 1,
                "successful_messages": 1 if had_access else 0,
                "blocked_messages": 0 if had_access else 1
            }

        await self._save_users(users)
        self._cache[user_id] = users[user_key]

    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получает информацию о пользователе"""
        if user_id in self._cache:
            return self._cache[user_id]

        users = await self._load_users()
        return users.get(str(user_id))

    async def get_all_users(self) -> List[Dict]:
        """Получает список всех пользователей"""
        users = await self._load_users()
        return list(users.values())

    async def get_active_users(self, days: int = 7) -> List[Dict]:
        """Получает список активных пользователей за последние N дней"""
        from datetime import timedelta

        users = await self._load_users()
        cutoff_date = datetime.now() - timedelta(days=days)

        active = []
        for user_data in users.values():
            last_seen = datetime.fromisoformat(user_data["last_seen"])
            if last_seen >= cutoff_date:
                active.append(user_data)

        # Сортируем по последней активности
        active.sort(key=lambda x: x["last_seen"], reverse=True)

        return active

    async def get_blocked_users(self) -> List[Dict]:
        """Получает пользователей, у которых были заблокированные сообщения"""
        users = await self._load_users()

        blocked = []
        for user_data in users.values():
            if user_data.get("blocked_messages", 0) > 0:
                blocked.append(user_data)

        # Сортируем по количеству заблокированных
        blocked.sort(key=lambda x: x.get("blocked_messages", 0), reverse=True)

        return blocked

    async def get_statistics(self) -> Dict:
        """Получает общую статистику по пользователям"""
        users = await self._load_users()

        total_users = len(users)
        total_messages = sum(u.get("message_count", 0) for u in users.values())
        successful_messages = sum(u.get("successful_messages", 0) for u in users.values())
        blocked_messages = sum(u.get("blocked_messages", 0) for u in users.values())

        active_7d = await self.get_active_users(7)
        active_30d = await self.get_active_users(30)

        return {
            "total_users": total_users,
            "total_messages": total_messages,
            "successful_messages": successful_messages,
            "blocked_messages": blocked_messages,
            "active_7d": len(active_7d),
            "active_30d": len(active_30d)
        }