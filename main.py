import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage as FSMMemoryStorage
from pathlib import Path

from config import TELEGRAM_TOKEN, ADMIN_USER_IDS
from bot.handlers import router as main_router
from bot.admin_panel import router as admin_router
from utils.admin_notifications import admin_notifier

# Optional: run FastAPI admin panel alongside the bot
try:
    from admin_panel_web import app as admin_app
    HAVE_ADMIN_WEB = True
except Exception:
    admin_app = None
    HAVE_ADMIN_WEB = False

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mahiro_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Создаём необходимые папки
Path("data").mkdir(exist_ok=True)
Path("assets/mahiro").mkdir(parents=True, exist_ok=True)
for mood in ["happy", "shy", "angry", "tired", "sleepy", "excited", "sad", "neutral"]:
    Path(f"assets/mahiro/{mood}").mkdir(parents=True, exist_ok=True)


async def main():
    """Точка входа"""
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN не установлен в .env файле!")
        return
    
    # Инициализация FSM хранилища
    storage = FSMMemoryStorage()
    
    # Инициализация бота
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Инициализируем систему уведомлений
    admin_notifier.set_bot(bot)
    admin_notifier.set_admins(ADMIN_USER_IDS)
    
    # Регистрация роутеров (ВАЖНО: admin_router ПЕРВЫМ!)
    from bot.minigames import router as minigames_router
    dp.include_router(admin_router)
    dp.include_router(minigames_router)
    dp.include_router(main_router)
    
    # Настройка команд и меню
    from aiogram.types import BotCommand, MenuButtonCommands
    commands = [
        BotCommand(command="start", description="Начать общение"),
        BotCommand(command="mood", description="Проверить настроение"),
        BotCommand(command="stats", description="Твоя статистика"),
        BotCommand(command="donate", description="Поддержать разработку ⭐"),
        BotCommand(command="balance", description="Баланс звёзд"),
        BotCommand(command="help", description="Помощь")
    ]
    await bot.set_my_commands(commands)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    
    logger.info("=" * 50)
    logger.info("🎀 Бот Махиро запущен!")
    logger.info("🎛 Админ-панель: /admin")
    logger.info("=" * 50)
    # Запуск web admin (uvicorn) если доступно
    admin_task = None
    if HAVE_ADMIN_WEB:
        try:
            import uvicorn

            async def _run_admin():
                config = uvicorn.Config(app=admin_app, host="127.0.0.1", port=8000, log_level="info")
                server = uvicorn.Server(config)
                await server.serve()

            admin_task = asyncio.create_task(_run_admin())
            logger.info("Запущен встроенный admin web на http://127.0.0.1:8000 (если установлены зависимости)")
        except Exception as e:
            logger.warning(f"Не удалось запустить admin web: {e}")

    # Запуск polling
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        # Останавливаем web-сервер, если он запущен
        if admin_task:
            admin_task.cancel()
            try:
                await admin_task
            except asyncio.CancelledError:
                pass
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)