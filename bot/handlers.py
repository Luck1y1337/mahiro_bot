from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import logging
import random

from utils.services import (
    mistral_client, memory, trust_system, mood_system, message_counter,
    long_term_memory, image_manager, statistics, rate_limiter, trigger_system, user_tracker
)
from utils.admin_notifications import admin_notifier
from utils.donations import donation_system
from bot.filters import IsNotBlacklisted, IsAdmin
from config import MAX_HISTORY_MESSAGES

logger = logging.getLogger(__name__)

router = Router()

from ai.prompts import get_system_prompt
from ai.context_builder import get_time_of_day, format_history_for_context


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
    
    # Проверяем, новый ли пользователь
    user_info = await user_tracker.get_user_info(user_id)
    if user_info and user_info.get('message_count', 0) == 1:
        # Это первое сообщение - новый пользователь!
        await admin_notifier.notify_new_user(
            user_id,
            message.from_user.username or "нет",
            message.from_user.first_name or "Аноним"
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
    
    # Кнопки быстрого доступа
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/mood"), KeyboardButton(text="/stats")],
            [KeyboardButton(text="/donate"), KeyboardButton(text="/help")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Напиши что-нибудь..."
    )
    
    await message.answer(
        "Э-э… привет? 😳\n"
        "Я Махиро… с кем я разговариваю?\n\n"
        "(можешь просто написать мне что-нибудь)",
        reply_markup=keyboard
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
    
    help_text = """🎀 Команды бота Махиро:

/start - начать общение
/reset - очистить историю
/mood - проверить настроение
/stats - твоя статистика
/donate - поддержать разработку ⭐
/balance - баланс звёзд
/help - эта справка

Просто пиши мне, и я отвечу! 😊
"""
    await message.answer(help_text, parse_mode="Markdown")


# ========== ДОНАТЫ ЧЕРЕЗ TELEGRAM STARS ==========

@router.message(Command("donate"))
async def cmd_donate(message: Message):
    """Команда /donate - донат через Stars"""
    args = message.text.split()

    if len(args) >= 2:
        try:
            stars_amount = int(args[1])

            if stars_amount < 1:
                await message.answer("💫 Минимум 1 звезда!")
                return

            if stars_amount > 2500:
                await message.answer("💫 Максимум 2500 звёзд за раз!")
                return

            await message.answer_invoice(
                title="Поддержка Махиро",
                description=f"Донат {stars_amount} звёзд",
                payload=f"stars_{message.from_user.id}",
                currency="XTR",
                prices=[LabeledPrice(label=f"{stars_amount} ⭐", amount=stars_amount)]
            )
            return

        except ValueError:
            await message.answer("❌ Укажи число: /donate 10")
            return
        except Exception as e:
            logger.error(f"Invoice error: {e}")
            await message.answer("❌ Ошибка. Попробуй через кнопки")
            return

    balance = await donation_system.get_balance(message.from_user.id)
    total_donated = await donation_system.get_total_donated(message.from_user.id)

    text = (
        f"💫 ПОДДЕРЖКА МАХИРО\n\n"
        f"⭐ Баланс: {balance}\n"
        f"💰 Задонатил: {total_donated}\n\n"
        f"Выбери сумму или введи:\n/donate 25"
    )

    keyboard = [
        [
            InlineKeyboardButton(text="⭐ 1", callback_data="donate_1"),
            InlineKeyboardButton(text="⭐ 5", callback_data="donate_5"),
            InlineKeyboardButton(text="⭐ 10", callback_data="donate_10"),
        ],
        [
            InlineKeyboardButton(text="⭐ 50", callback_data="donate_50"),
            InlineKeyboardButton(text="⭐ 100", callback_data="donate_100"),
        ],
        [InlineKeyboardButton(text="🏆 Топ", callback_data="top_donors")],
    ]

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data.startswith("donate_"))
async def process_donate_button(callback: CallbackQuery):
    """Кнопки донатов"""
    try:
        stars_amount = int(callback.data.split("_")[1])

        await callback.message.answer_invoice(
            title="Поддержка Махиро",
            description=f"Донат {stars_amount} звёзд",
            payload=f"stars_{callback.from_user.id}",
            currency="XTR",
            prices=[LabeledPrice(label=f"{stars_amount} ⭐", amount=stars_amount)]
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Button error: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Успешная оплата"""
    try:
        payment = message.successful_payment
        stars = payment.total_amount

        await donation_system.record_donation(
            user_id=message.from_user.id,
            username=message.from_user.username or "нет",
            first_name=message.from_user.first_name or "Аноним",
            stars_amount=stars,
            transaction_id=payment.telegram_payment_charge_id
        )

        thanks = [
            f"Спасибо за {stars} звёзд! 😳💖",
            f"Вау, {stars} звёзд! Спасибо! 😊",
            f"Благодарю! {stars} звёзд! 💫"
        ]

        balance = await donation_system.get_balance(message.from_user.id)

        await message.answer(
            f"{random.choice(thanks)}\n\n⭐ Баланс: {balance}"
        )

        await admin_notifier.notify_custom(
            f"💰 Донат {stars} ⭐\n👤 {message.from_user.first_name}"
        )

    except Exception as e:
        logger.error(f"Payment error: {e}")
        await message.answer("❌ Ошибка")


@router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Одобрение платежа"""
    await pre_checkout_query.answer(ok=True)


@router.callback_query(F.data == "top_donors")
async def show_top_donors(callback: CallbackQuery):
    """Топ донатеров"""
    top = await donation_system.get_top_donors(10)

    if not top:
        text = "🏆 ТОП ДОНАТЕРОВ\n\nПока пусто"
    else:
        text = "🏆 ТОП ДОНАТЕРОВ\n\n"
        medals = ["🥇", "🥈", "🥉"]

        for i, d in enumerate(top, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            text += f"{medal} {d['first_name']} — ⭐ {d['total_stars']}\n"

    await callback.message.answer(text)
    await callback.answer()


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    """Баланс звёзд"""
    balance = await donation_system.get_balance(message.from_user.id)
    total = await donation_system.get_total_donated(message.from_user.id)

    await message.answer(
        f"💫 БАЛАНС\n\n⭐ Звёзд: {balance}\n💰 Задонатил: {total}"
    )

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========

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