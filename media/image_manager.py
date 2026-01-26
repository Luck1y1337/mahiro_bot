import random
from pathlib import Path
from typing import Optional, List
import logging

from aiogram.types import FSInputFile
from config import IMAGES_FOLDER, IMAGES_ENABLED, IMAGE_SEND_CHANCE

logger = logging.getLogger(__name__)


class ImageManager:
    """
    Управление отправкой картинок Махиро
    """

    def __init__(self, images_folder: str = IMAGES_FOLDER):
        self.images_folder = Path(images_folder)
        self.images_folder.mkdir(parents=True, exist_ok=True)
        self.enabled = IMAGES_ENABLED

        # Категории картинок
        self.categories = {
            "happy": "happy",  # счастливые
            "shy": "shy",  # смущённые
            "angry": "angry",  # раздражённые
            "tired": "tired",  # усталые
            "sleepy": "sleepy",  # сонные
            "excited": "excited",  # взволнованные
            "sad": "sad",  # грустные
            "neutral": "neutral"  # нейтральные
        }

        # Создаём подпапки для категорий
        for category in self.categories.values():
            (self.images_folder / category).mkdir(exist_ok=True)

    def get_images_for_mood(self, mood: str) -> List[Path]:
        """
        Получает список картинок для настроения

        Args:
            mood: настроение Махиро

        Returns:
            Список путей к картинкам
        """
        # Маппинг настроения на категорию
        mood_to_category = {
            "счастливая": "happy",
            "раздражённая": "angry",
            "усталая": "tired",
            "сонная": "sleepy",
            "взволнованная": "excited",
            "грустная": "sad",
            "обычное": "neutral"
        }

        category = mood_to_category.get(mood, "neutral")
        category_path = self.images_folder / category

        # Получаем все изображения из категории
        images = list(category_path.glob("*.jpg")) + \
                 list(category_path.glob("*.jpeg")) + \
                 list(category_path.glob("*.png")) + \
                 list(category_path.glob("*.webp"))

        return images

    def get_random_image(self, mood: str) -> Optional[Path]:
        """
        Получает случайную картинку для настроения

        Args:
            mood: настроение Махиро

        Returns:
            Путь к картинке или None
        """
        if not self.enabled:
            return None

        images = self.get_images_for_mood(mood)

        if not images:
            logger.warning(f"Нет картинок для настроения: {mood}")
            # Пробуем взять из neutral
            images = self.get_images_for_mood("обычное")

        if not images:
            logger.warning("Нет картинок вообще!")
            return None

        return random.choice(images)

    def should_send_image(self, trigger: str = None) -> bool:
        """
        Определяет, нужно ли отправить картинку

        Args:
            trigger: триггер, если есть

        Returns:
            True, если нужно отправить картинку
        """
        if not self.enabled:
            return False

        # Всегда отправляем, если есть триггер на внешность
        if trigger and any(word in trigger.lower() for word in ["милая", "красивая", "симпатичная", "прелесть"]):
            return True

        # Случайно отправляем с настроенным шансом
        return random.random() < IMAGE_SEND_CHANCE

    async def send_image(self, bot, chat_id: int, mood: str, caption: str = None):
        """
        Отправляет картинку в чат

        Args:
            bot: объект бота
            chat_id: ID чата
            mood: настроение
            caption: подпись к картинке
        """
        if not self.enabled:
            return

        image_path = self.get_random_image(mood)

        if not image_path:
            logger.warning("Не удалось найти картинку для отправки")
            return

        try:
            photo = FSInputFile(image_path)
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption
            )
            logger.info(f"Отправлена картинка: {image_path.name}")
        except Exception as e:
            logger.error(f"Ошибка отправки картинки: {e}")

    def get_statistics(self) -> dict:
        """Возвращает статистику по картинкам"""
        stats = {}

        for mood, category in [
            ("счастливая", "happy"),
            ("раздражённая", "angry"),
            ("усталая", "tired"),
            ("сонная", "sleepy"),
            ("взволнованная", "excited"),
            ("грустная", "sad"),
            ("обычное", "neutral")
        ]:
            images = self.get_images_for_mood(mood)
            stats[mood] = len(images)

        return stats