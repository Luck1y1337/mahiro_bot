from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import logging

from ai.mistral_client import MistralClient
from ai.prompts import get_system_prompt
from ai.context_builder import get_time_of_day, format_history_for_context
from memory.storage import MemoryStorage
from memory.trust_system import TrustSystem
from memory.mood_system import MoodSystem, MessageCounter
from config import MAX_HISTORY_MESSAGES

logger = logging.getLogger(__name__)

router = Router()

# Инициализация компонентов
mistral_client = MistralClient()
memory = MemoryStorage()
trust_system = TrustSystem()
mood_system = MoodSystem()
message_counter = MessageCounter()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    await message.answer(
        "Э-э… привет? 😳\n"
        "Я Махиро… с кем я разговариваю?\n\n"
        "(можешь просто написать мне что-нибудь)"
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Команда /reset - очистка истории"""
    user_id = message.from_user.id
    await memory.save_history(user_id, [])

    await message.answer(
        "Хм… начнём сначала? 😅\n"
        "(история диалога очищена)"
    )


@router.message(Command("mood"))
async def cmd_mood(message: Message):
    """Команда /mood - проверить настроение"""
    user_id = message.from_user.id
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


@router.message(Command("setmood"))
async def cmd_setmood(message: Message):
    """Команда /setmood <настроение> - установить настроение вручную"""
    user_id = message.from_user.id

    # Парсим аргумент
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
        await message.answer(
            f"Неизвестное настроение: {mood}\n"
            f"Доступные: {', '.join(MoodSystem.MOODS)}"
        )
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
    """Команда /stats - статистика"""
    user_id = message.from_user.id

    trust = await trust_system.get_trust(user_id)
    mood = await mood_system.get_mood(user_id)
    history = await memory.load_history(user_id)
    msg_count = await message_counter.get_count(user_id)

    stats_text = (
        "📊 Статистика нашего общения:\n\n"
        f"💬 Сообщений в истории: {len(history)}\n"
        f"📅 Сообщений сегодня: {msg_count}\n"
        f"❤️ Уровень доверия: {trust:.0%}\n"
        f"😊 Настроение: {mood}\n"
    )

    await message.answer(stats_text)


@router.message(F.text)
async def handle_message(message: Message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_text = message.text

    try:
        # Показываем "печатает..."
        await message.bot.send_chat_action(message.chat.id, "typing")

        # Инкрементируем счётчик сообщений
        msg_count = await message_counter.increment(user_id)

        # Получаем контекст
        time_of_day = get_time_of_day()
        trust_level = await trust_system.get_trust(user_id)
        history = await memory.load_history(user_id)

        # 🎭 ВЫЧИСЛЯЕМ НАСТРОЕНИЕ
        mood = await mood_system.calculate_mood(
            user_id=user_id,
            message_text=user_text,
            time_of_day=time_of_day,
            trust_level=trust_level,
            message_count_today=msg_count
        )

        logger.info(f"User {user_id}: mood={mood}, trust={trust_level:.2f}, messages_today={msg_count}")

        # Генерируем system prompt с учётом настроения
        system_prompt = get_system_prompt(time_of_day, trust_level, mood)

        # Форматируем историю для API
        formatted_history = format_history_for_context(history, MAX_HISTORY_MESSAGES)

        # Генерируем ответ через Mistral
        response = await mistral_client.generate_response(
            system_prompt=system_prompt,
            history=formatted_history,
            user_message=user_text
        )

        if response:
            # Отправляем ответ
            await message.answer(response)

            # Сохраняем в историю
            await memory.add_message(user_id, "user", user_text, MAX_HISTORY_MESSAGES)
            await memory.add_message(user_id, "assistant", response, MAX_HISTORY_MESSAGES)

            # Увеличиваем доверие
            await trust_system.increment_trust(user_id)
        else:
            await message.answer(
                "А-ай… что-то у меня в голове помутилось… 😖\n"
                "Можешь повторить?"
            )

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await message.answer(
            "Э-эй… что-то пошло не так… 💢\n"
            "(внутренняя ошибка)"
        )