import logging
from typing import Optional
from aiogram import Bot

logger = logging.getLogger(__name__)


class AdminNotifier:
    """Система уведомлений для администратора"""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.admin_ids = []
        self.enabled = True
    
    def set_bot(self, bot: Bot):
        """Устанавливает экземпляр бота"""
        self.bot = bot
    
    def set_admins(self, admin_ids: list):
        """Устанавливает список админов"""
        self.admin_ids = admin_ids
    
    def disable(self):
        """Отключает уведомления"""
        self.enabled = False
    
    def enable(self):
        """Включает уведомления"""
        self.enabled = True
    
    async def notify_new_user(self, user_id: int, username: str, first_name: str):
        """Уведомление о новом пользователе"""
        if not self.enabled or not self.bot:
            return
        
        message = (
            f"🆕 Новый пользователь!\n\n"
            f"👤 {first_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📝 Username: @{username if username else 'нет'}"
        )
        
        await self._send_to_admins(message)
    
    async def notify_error(self, error: str, user_id: int = None):
        """Уведомление об ошибке"""
        if not self.enabled or not self.bot:
            return
        
        message = f"❌ Ошибка в боте!\n\n"
        if user_id:
            message += f"Пользователь: {user_id}\n"
        message += f"Ошибка: {error[:500]}"
        
        await self._send_to_admins(message)
    
    async def notify_blocked_attempt(self, user_id: int, username: str, reason: str):
        """Уведомление о заблокированной попытке"""
        if not self.enabled or not self.bot:
            return
        
        message = (
            f"🚫 Заблокирована попытка доступа!\n\n"
            f"👤 ID: {user_id}\n"
            f"📝 Username: @{username if username else 'нет'}\n"
            f"❓ Причина: {reason}"
        )
        
        await self._send_to_admins(message)
    
    async def notify_rate_limit(self, user_id: int, username: str):
        """Уведомление о превышении лимита"""
        if not self.enabled or not self.bot:
            return
        
        message = (
            f"⚠️ Превышен лимит запросов!\n\n"
            f"👤 ID: {user_id}\n"
            f"📝 Username: @{username if username else 'нет'}"
        )
        
        await self._send_to_admins(message)
    
    async def notify_milestone(self, milestone_type: str, value: int):
        """Уведомление о достижении"""
        if not self.enabled or not self.bot:
            return
        
        milestones = {
            "users": f"🎉 {value} пользователей зарегистрировано!",
            "messages": f"💬 {value} сообщений обработано!",
            "uptime": f"⏱ Бот работает {value} дней!"
        }
        
        message = milestones.get(milestone_type, f"🎯 Достижение: {milestone_type} = {value}")
        
        await self._send_to_admins(message)
    
    async def notify_custom(self, message: str):
        """Произвольное уведомление"""
        if not self.enabled or not self.bot:
            return
        
        await self._send_to_admins(message)
    
    async def _send_to_admins(self, message: str):
        """Отправляет сообщение всем админам"""
        if not self.bot or not self.admin_ids:
            return
        
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(admin_id, message)
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")


# Глобальный экземпляр
admin_notifier = AdminNotifier()