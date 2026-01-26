from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import logging

from ai.mistral_client import MistralClient
from ai.prompts import get_system_prompt
from ai.context_builder import get_time_of_day, format_history_for_context
from ai.triggers import TriggerSystem
from memory.storage import MemoryStorage
from memory.trust_system import TrustSystem
from memory.mood_system import MoodSystem, MessageCounter
from memory.long_term_memory import LongTermMemory
from media.image_manager import ImageManager
from utils.statistics import Statistics
from utils.rate_limiter import RateLimiter
from utils.user_tracker import UserTracker
from bot.filters import IsNotBlacklisted, IsAdmin
from config import MAX_HISTORY_MESSAGES

logger = logging.getLogger(__name__)

router = Router()

# Инициализация компонентов
mistral_client = MistralClient()
memory = MemoryStorage()
trust_system = TrustSystem()
mood_system = MoodSystem()
message_counter = MessageCounter()
long_term_memory = LongTermMemory()
image_manager = ImageManager()
statistics = Statistics()
rate_limiter = RateLimiter()
trigger_system = TriggerSystem()
user_tracker = UserTracker()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id

    # Проверка доступа
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS, BLACKLIST_USER_IDS, ADMIN_USER_IDS

    # Трекаем пользователя
    await user_tracker.track_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
        had_access=True
    )

    if user_id in BLACKLIST_USER_IDS:
        await message.answer("🚫 Доступ запрещён.")
        return

    if ENABLE_WHITELIST and user_id not in ADMIN_USER_IDS and user_id not in WHITELIST_USER_IDS:
        await message.answer(
            "🔐 Доступ ограничен.\n\n"
            "Этот бот использует белый список пользователей.\n"
            "Обратитесь к администратору для получения доступа."
        )
        return

    await statistics.add_user()

    await message.answer(
        "Э-э… привет? 😳\n"
        "Я Махиро… с кем я разговариваю?\n\n"
        "(можешь просто написать мне что-нибудь)"
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Команда /reset - очистка истории"""
    user_id = message.from_user.id

    # Проверка доступа
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS, BLACKLIST_USER_IDS, ADMIN_USER_IDS
    if user_id in BLACKLIST_USER_IDS:
        return
    if ENABLE_WHITELIST and user_id not in ADMIN_USER_IDS and user_id not in WHITELIST_USER_IDS:
        return

    await memory.save_history(user_id, [])

    await message.answer(
        "Хм… начнём сначала? 😅\n"
        "(история диалога очищена)"
    )


@router.message(Command("mood"))
async def cmd_mood(message: Message):
    """Команда /mood - проверить настроение"""
    user_id = message.from_user.id

    # Проверка доступа
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS, BLACKLIST_USER_IDS, ADMIN_USER_IDS
    if user_id in BLACKLIST_USER_IDS:
        return
    if ENABLE_WHITELIST and user_id not in ADMIN_USER_IDS and user_id not in WHITELIST_USER_IDS:
        return

    current_mood = await mood_system.get_mood(user_id)
    trust_level = await trust_system.get_trust(user_id)

    mood_emojis = {
        "обычное": "😐",
        "счастливая": "😊",
        "раздражённая": "😤",
        "усталая": "😮‍💨",
        "сонная": "😴",
        "взволнованная": "😳",
        "грустная": "😔"
    }

    emoji = mood_emojis.get(current_mood, "😐")

    response = f"Эм… сейчас я {current_mood} {emoji}\n"
    response += f"Мы общаемся уже какое-то время… доверие: {trust_level:.0%}"

    await message.answer(response)


@router.message(Command("setmood"), IsAdmin())
async def cmd_setmood(message: Message):
    """Команда /setmood <настроение> - установить настроение вручную (админы)"""
    user_id = message.from_user.id

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Использование: /setmood <настроение>\n\n"
            "Доступные настроения:\n"
            "• обычное\n"
            "• счастливая\n"
            "• раздражённая\n"
            "• усталая\n"
            "• сонная\n"
            "• взволнованная\n"
            "• грустная"
        )
        return

    mood = args[1].strip().lower()

    if mood not in MoodSystem.MOODS:
        await message.answer(f"Неизвестное настроение: {mood}")
        return

    await mood_system.set_mood(user_id, mood)

    mood_responses = {
        "обычное": "Хорошо… вернулась в обычное состояние 😐",
        "счастливая": "Ура! Теперь я в хорошем настроении! 😊",
        "раздражённая": "Ладно… я теперь раздражена 😤",
        "усталая": "Уф… я так устала… 😮‍💨",
        "сонная": "*зевает* Мне так спать хочется… 😴",
        "взволнованная": "О-ой! Что-то волнуюсь! 😳",
        "грустная": "Эх… немного грустно стало… 😔"
    }

    await message.answer(mood_responses.get(mood, "Настроение изменено"))


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Команда /stats - статистика пользователя"""
    user_id = message.from_user.id

    # Проверка доступа
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS, BLACKLIST_USER_IDS, ADMIN_USER_IDS
    if user_id in BLACKLIST_USER_IDS:
        return
    if ENABLE_WHITELIST and user_id not in ADMIN_USER_IDS and user_id not in WHITELIST_USER_IDS:
        return

    trust = await trust_system.get_trust(user_id)
    mood = await mood_system.get_mood(user_id)
    history = await memory.load_history(user_id)
    msg_count = await message_counter.get_count(user_id)
    user_memory = await long_term_memory.get_memory(user_id)

    stats_text = "📊 Статистика нашего общения:\n\n"
    stats_text += f"💬 Сообщений в истории: {len(history)}\n"
    stats_text += f"📅 Сообщений сегодня: {msg_count}\n"
    stats_text += f"❤️ Уровень доверия: {trust:.0%}\n"
    stats_text += f"😊 Настроение: {mood}\n"

    if user_memory["name"]:
        stats_text += f"\n👤 Я знаю, что тебя зовут: {user_memory['name']}"

    if user_memory["facts"]:
        stats_text += f"\n📝 Фактов о тебе: {len(user_memory['facts'])}"

    await message.answer(stats_text)


@router.message(Command("botstats"), IsAdmin())
async def cmd_botstats(message: Message):
    """Команда /botstats - общая статистика бота (только админы)"""
    stats_text = await statistics.format_stats()
    await message.answer(stats_text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help - помощь"""
    user_id = message.from_user.id

    # Проверка доступа
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS, BLACKLIST_USER_IDS, ADMIN_USER_IDS
    if user_id in BLACKLIST_USER_IDS:
        return
    if ENABLE_WHITELIST and user_id not in ADMIN_USER_IDS and user_id not in WHITELIST_USER_IDS:
        return

    help_text = """🎀 **Команды бота Махиро:**

/start - начать общение
/reset - очистить историю
/mood - проверить настроение
/stats - твоя статистика
/help - эта справка

Просто пиши мне, и я отвечу! 😊
"""
    await message.answer(help_text, parse_mode="Markdown")


@router.message(F.text)
async def handle_message(message: Message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_text = message.text
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Проверяем доступ ДО rate limit
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS, BLACKLIST_USER_IDS, ADMIN_USER_IDS

    # Проверка blacklist (приоритет)
    if user_id in BLACKLIST_USER_IDS:
        await user_tracker.track_user(user_id, username, first_name, last_name, had_access=False)
        await message.answer("🚫 Доступ запрещён.")
        return

    # Проверка whitelist
    if ENABLE_WHITELIST:
        if user_id not in ADMIN_USER_IDS and user_id not in WHITELIST_USER_IDS:
            await user_tracker.track_user(user_id, username, first_name, last_name, had_access=False)
            await message.answer(
                "🔐 Доступ ограничен.\n\n"
                "Этот бот использует белый список пользователей.\n"
                "Обратитесь к администратору для получения доступа."
            )
            return

    # Трекаем пользователя (доступ разрешён)
    await user_tracker.track_user(user_id, username, first_name, last_name, had_access=True)

    # Проверка rate limit
    allowed, reason = rate_limiter.is_allowed(user_id)
    if not allowed:
        await message.answer(f"Эй! {reason} 😤")
        return

    try:
        await message.bot.send_chat_action(message.chat.id, "typing")

        # Записываем сообщение
        rate_limiter.record_message(user_id)
        msg_count = await message_counter.increment(user_id)

        # Получаем контекст
        time_of_day = get_time_of_day()
        trust_level = await trust_system.get_trust(user_id)
        history = await memory.load_history(user_id)

        # Вычисляем настроение
        mood = await mood_system.calculate_mood(
            user_id=user_id,
            message_text=user_text,
            time_of_day=time_of_day,
            trust_level=trust_level,
            message_count_today=msg_count
        )

        # Проверяем триггеры
        trigger_response = trigger_system.check_triggers(user_text, trust_level)

        if trigger_response:
            # Триггер сработал - отправляем готовый ответ
            await message.answer(trigger_response)

            # Возможно, отправим картинку
            if image_manager.should_send_image(user_text):
                await image_manager.send_image(
                    bot=message.bot,
                    chat_id=message.chat.id,
                    mood=mood
                )
                await statistics.increment_images()

            # Сохраняем в историю
            await memory.add_message(user_id, "user", user_text, MAX_HISTORY_MESSAGES)
            await memory.add_message(user_id, "assistant", trigger_response, MAX_HISTORY_MESSAGES)
            await trust_system.increment_trust(user_id)
            await statistics.increment_messages(mood)

            logger.info(f"Trigger response sent to {user_id}")
            return

        # Генерируем system prompt
        system_prompt = get_system_prompt(time_of_day, trust_level, mood)

        # Добавляем долгосрочную память
        ltm_context = await long_term_memory.get_context_string(user_id)
        if ltm_context:
            system_prompt += ltm_context

        # Форматируем историю
        formatted_history = format_history_for_context(history, MAX_HISTORY_MESSAGES)

        # Генерируем ответ
        response = await mistral_client.generate_response(
            system_prompt=system_prompt,
            history=formatted_history,
            user_message=user_text
        )

        if response:
            await message.answer(response)

            # Возможно, отправим картинку
            if image_manager.should_send_image():
                await image_manager.send_image(
                    bot=message.bot,
                    chat_id=message.chat.id,
                    mood=mood,
                    caption="(нашла картинку! 😊)"
                )
                await statistics.increment_images()

            # Сохраняем
            await memory.add_message(user_id, "user", user_text, MAX_HISTORY_MESSAGES)
            await memory.add_message(user_id, "assistant", response, MAX_HISTORY_MESSAGES)
            await trust_system.increment_trust(user_id)
            await statistics.increment_messages(mood)

            logger.info(f"Response sent to {user_id}: mood={mood}, trust={trust_level:.2f}")
        else:
            await message.answer("А-ай… что-то у меня в голове помутилось… 😖\nМожешь повторить?")
            await statistics.increment_errors()

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения от {user_id}: {e}", exc_info=True)
        await message.answer("Э-эй… что-то пошло не так… 💢")
        await statistics.increment_errors()