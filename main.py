import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import TELEGRAM_TOKEN
from bot.handlers import router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Точка входа"""
    # Инициализация бота
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(router)

    logger.info("Бот Махиро запущен! 🎀")

    # Запуск polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())