from aiogram.filters import Filter
from aiogram.types import Message

from config import ADMIN_USER_IDS, BLACKLIST_USER_IDS, ENABLE_WHITELIST, WHITELIST_USER_IDS


class IsAdmin(Filter):
    """Фильтр: пользователь - админ"""

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_USER_IDS


class IsNotBlacklisted(Filter):
    """Фильтр: пользователь не в чёрном списке"""

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id not in BLACKLIST_USER_IDS


class IsWhitelisted(Filter):
    """
    Фильтр: пользователь в белом списке
    """

    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id

        if not ENABLE_WHITELIST:
            return True

        if user_id in ADMIN_USER_IDS:
            return True

        return user_id in WHITELIST_USER_IDS


class HasAccess(Filter):
    """
    Комбинированный фильтр (НЕ ИСПОЛЬЗУЕТСЯ В НОВОЙ ВЕРСИИ)
    Оставлен для совместимости
    """

    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id

        if user_id in BLACKLIST_USER_IDS:
            return False

        if not ENABLE_WHITELIST:
            return True

        if user_id in ADMIN_USER_IDS:
            return True

        return user_id in WHITELIST_USER_IDS