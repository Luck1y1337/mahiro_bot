from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from pathlib import Path
from datetime import datetime
import logging

from bot.filters import IsAdmin
from utils.statistics import Statistics
from utils.user_tracker import UserTracker
from memory.trust_system import TrustSystem
from memory.mood_system import MoodSystem
from memory.storage import MemoryStorage
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

router = Router()

# Инициализация компонентов
statistics = Statistics()
user_tracker = UserTracker()
trust_system = TrustSystem()
mood_system = MoodSystem()
memory = MemoryStorage()
rate_limiter = RateLimiter()


# FSM для добавления/удаления пользователей
class AdminStates(StatesGroup):
    waiting_for_whitelist_add = State()
    waiting_for_whitelist_remove = State()
    waiting_for_blacklist_add = State()
    waiting_for_blacklist_remove = State()
    waiting_for_user_info = State()
    waiting_for_broadcast = State()


def get_main_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню админ-панели"""
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="💰 Донаты", callback_data="admin_donations")],
        [InlineKeyboardButton(text="🔐 Whitelist", callback_data="admin_whitelist_menu")],
        [InlineKeyboardButton(text="🚫 Blacklist", callback_data="admin_blacklist_menu")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_whitelist_menu() -> InlineKeyboardMarkup:
    """Меню Whitelist"""
    # Читаем напрямую из .env
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    enable_whitelist = os.getenv("ENABLE_WHITELIST", "false").lower() == "true"
    whitelist_ids_str = os.getenv("WHITELIST_USER_IDS", "")
    whitelist_count = len([x for x in whitelist_ids_str.split(",") if x.strip()])
    
    status = "✅ Вкл" if enable_whitelist else "❌ Выкл"
    
    keyboard = [
        [InlineKeyboardButton(text=f"🔐 Whitelist: {status}", callback_data="admin_toggle_whitelist")],
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="admin_whitelist_add")],
        [InlineKeyboardButton(text="➖ Удалить пользователя", callback_data="admin_whitelist_remove")],
        [InlineKeyboardButton(text=f"📋 Список ({whitelist_count})", callback_data="admin_list_whitelist")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_blacklist_menu() -> InlineKeyboardMarkup:
    """Меню Blacklist"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    blacklist_ids_str = os.getenv("BLACKLIST_USER_IDS", "")
    blacklist_count = len([x for x in blacklist_ids_str.split(",") if x.strip()])
    
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить в Blacklist", callback_data="admin_blacklist_add")],
        [InlineKeyboardButton(text="➖ Удалить из Blacklist", callback_data="admin_blacklist_remove")],
        [InlineKeyboardButton(text=f"📋 Список ({blacklist_count})", callback_data="admin_list_blacklist")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton(text="🖼 Статистика картинок", callback_data="admin_images_stats")],
        [InlineKeyboardButton(text="📊 Подробная статистика", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton(text="💾 Экспорт данных", callback_data="admin_export_data")],
        [InlineKeyboardButton(text="⚙️ Массовые операции", callback_data="admin_mass_operations")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="admin_notifications_toggle")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_back_button(callback_data: str = "admin_main") -> InlineKeyboardMarkup:
    """Кнопка назад"""
    keyboard = [[InlineKeyboardButton(text="« Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(Command("admin"), IsAdmin())
async def cmd_admin(message: Message):
    """Команда /admin - открыть админ-панель"""
    text = (
        "🎛 АДМИН-ПАНЕЛЬ МАХИРО\n\n"
        "Добро пожаловать в панель управления!\n"
        "Выберите нужный раздел:"
    )
    
    await message.answer(text, reply_markup=get_main_admin_menu())


@router.callback_query(F.data == "admin_main", IsAdmin())
async def admin_main(callback: CallbackQuery):
    """Главное меню"""
    text = (
        "🎛 АДМИН-ПАНЕЛЬ МАХИРО\n\n"
        "Выберите нужный раздел:"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=get_main_admin_menu())
    except:
        pass
    await callback.answer()


@router.callback_query(F.data == "admin_stats", IsAdmin())
async def admin_stats(callback: CallbackQuery):
    """Показать статистику"""
    bot_stats = await statistics.get_stats()
    user_stats = await user_tracker.get_statistics()
    
    start_time = datetime.fromisoformat(bot_stats["start_time"])
    uptime = datetime.now() - start_time
    uptime_str = f"{uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м"
    
    text = f"""📊 СТАТИСТИКА БОТА

⏱ Время работы: {uptime_str}

Пользователи:
• 👥 Всего: {user_stats['total_users']}
• 🟢 Активных (7 дней): {user_stats['active_7d']}
• 🟢 Активных (30 дней): {user_stats['active_30d']}

Сообщения:
• 💬 Всего: {user_stats['total_messages']}
• ✅ Обработано: {user_stats['successful_messages']}
• 🚫 Заблокировано: {user_stats['blocked_messages']}

Система:
• 🖼 Картинок отправлено: {bot_stats['images_sent']}
• ❌ Ошибок: {bot_stats['errors']}
"""
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_main"))
    await callback.answer()


@router.callback_query(F.data == "admin_users_list", IsAdmin())
async def admin_users_list(callback: CallbackQuery):
    """Список всех пользователей"""
    users = await user_tracker.get_all_users()
    
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    admin_ids = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()]
    whitelist_ids = [int(x) for x in os.getenv("WHITELIST_USER_IDS", "").split(",") if x.strip()]
    blacklist_ids = [int(x) for x in os.getenv("BLACKLIST_USER_IDS", "").split(",") if x.strip()]
    
    if not users:
        text = "📭 Пользователей пока нет"
    else:
        users.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
        
        text = f"👥 ВСЕ ПОЛЬЗОВАТЕЛИ ({len(users)})\n\n"
        
        for user in users[:20]:
            user_id = user['user_id']
            username = user.get('username', 'нет')
            first_name = user.get('first_name', 'Аноним')
            msg_count = user.get('message_count', 0)
            blocked = user.get('blocked_messages', 0)
            
            status = []
            if user_id in admin_ids:
                status.append("👑")
            if user_id in whitelist_ids:
                status.append("✅")
            if user_id in blacklist_ids:
                status.append("🚫")
            
            status_str = " ".join(status) if status else "👤"
            
            text += f"{status_str} {first_name} (@{username})\n"
            text += f"   ID: {user_id} | 💬 {msg_count}"
            if blocked > 0:
                text += f" | 🚫 {blocked}"
            text += "\n\n"
        
        if len(users) > 20:
            text += f"\n...и ещё {len(users) - 20} пользователей"
    
    keyboard = [
        [InlineKeyboardButton(text="🚫 Заблокированные попытки", callback_data="admin_blocked_users")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data == "admin_blocked_users", IsAdmin())
async def admin_blocked_users(callback: CallbackQuery):
    """Пользователи с заблокированными сообщениями"""
    blocked = await user_tracker.get_blocked_users()
    
    if not blocked:
        text = "✅ Нет заблокированных попыток"
    else:
        text = f"🚫 ЗАБЛОКИРОВАННЫЕ ПОПЫТКИ ({len(blocked)})\n\n"
        
        for user in blocked[:15]:
            user_id = user['user_id']
            username = user.get('username', 'нет')
            first_name = user.get('first_name', 'Аноним')
            blocked_count = user.get('blocked_messages', 0)
            
            text += f"👤 {first_name} (@{username})\n"
            text += f"   ID: {user_id} | 🚫 {blocked_count} заблок.\n\n"
        
        if len(blocked) > 15:
            text += f"\n...и ещё {len(blocked) - 15}"
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_users_list"))
    await callback.answer()


@router.callback_query(F.data == "admin_whitelist_menu", IsAdmin())
async def admin_whitelist_menu(callback: CallbackQuery):
    """Меню Whitelist"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    enable_whitelist = os.getenv("ENABLE_WHITELIST", "false").lower() == "true"
    whitelist_ids_str = os.getenv("WHITELIST_USER_IDS", "")
    whitelist_count = len([x for x in whitelist_ids_str.split(",") if x.strip()])
    
    status = "✅ Включён" if enable_whitelist else "❌ Выключен"
    
    text = f"""🔐 УПРАВЛЕНИЕ WHITELIST

Статус: {status}
Пользователей в списке: {whitelist_count}

⚠️ Когда Whitelist включён:
• Только пользователи из списка могут использовать бота
• Админы ВСЕГДА имеют доступ
• Остальные получат отказ
"""
    
    await callback.message.edit_text(text, reply_markup=get_whitelist_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_blacklist_menu", IsAdmin())
async def admin_blacklist_menu(callback: CallbackQuery):
    """Меню Blacklist"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    blacklist_ids_str = os.getenv("BLACKLIST_USER_IDS", "")
    blacklist_count = len([x for x in blacklist_ids_str.split(",") if x.strip()])
    
    text = f"""🚫 УПРАВЛЕНИЕ BLACKLIST

Пользователей заблокировано: {blacklist_count}

⚠️ Пользователи из Blacklist:
• НЕ могут использовать бота
• Блокировка абсолютная
"""
    
    await callback.message.edit_text(text, reply_markup=get_blacklist_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_list_whitelist", IsAdmin())
async def admin_list_whitelist(callback: CallbackQuery):
    """Показать список Whitelist"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    enable_whitelist = os.getenv("ENABLE_WHITELIST", "false").lower() == "true"
    whitelist_ids_str = os.getenv("WHITELIST_USER_IDS", "")
    whitelist_ids = [int(x) for x in whitelist_ids_str.split(",") if x.strip()]
    
    if not enable_whitelist:
        text = "❌ Whitelist выключен\n\nВсе пользователи имеют доступ к боту."
    elif not whitelist_ids:
        text = "⚠️ Whitelist пуст\n\nТолько админы могут пользоваться ботом."
    else:
        text = f"📋 WHITELIST ({len(whitelist_ids)} польз.)\n\n"
        
        for user_id in whitelist_ids:
            user_info = await user_tracker.get_user_info(user_id)
            if user_info:
                name = user_info.get('first_name', 'Неизвестно')
                username = user_info.get('username', 'нет')
                text += f"• {name} (@{username})\n   ID: {user_id}\n\n"
            else:
                text += f"• ID: {user_id} (нет данных)\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_whitelist_menu"))
    await callback.answer()


@router.callback_query(F.data == "admin_list_blacklist", IsAdmin())
async def admin_list_blacklist(callback: CallbackQuery):
    """Показать список Blacklist"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    blacklist_ids_str = os.getenv("BLACKLIST_USER_IDS", "")
    blacklist_ids = [int(x) for x in blacklist_ids_str.split(",") if x.strip()]
    
    if not blacklist_ids:
        text = "✅ Blacklist пуст\n\nНет заблокированных пользователей."
    else:
        text = f"🚫 BLACKLIST ({len(blacklist_ids)} польз.)\n\n"
        
        for user_id in blacklist_ids:
            user_info = await user_tracker.get_user_info(user_id)
            if user_info:
                name = user_info.get('first_name', 'Неизвестно')
                username = user_info.get('username', 'нет')
                text += f"• {name} (@{username})\n   ID: {user_id}\n\n"
            else:
                text += f"• ID: {user_id} (нет данных)\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_blacklist_menu"))
    await callback.answer()


@router.callback_query(F.data == "admin_whitelist_add", IsAdmin())
async def admin_whitelist_add(callback: CallbackQuery, state: FSMContext):
    """Начать добавление в Whitelist"""
    text = (
        "➕ Добавить в Whitelist\n\n"
        "Отправьте Telegram ID пользователя.\n\n"
        "💡 Узнать ID: @userinfobot\n\n"
        "Отправьте /cancel для отмены"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_whitelist_add)
    await callback.answer()


@router.message(AdminStates.waiting_for_whitelist_add, IsAdmin())
async def process_whitelist_add(message: Message, state: FSMContext):
    """Обработка добавления в Whitelist"""
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом! Попробуйте ещё раз или /cancel")
        return
    
    result = await update_env_list("WHITELIST_USER_IDS", user_id, action="add")
    
    if result:
        await message.answer(
            f"✅ Пользователь {user_id} добавлен в Whitelist!\n\n"
            f"⚠️ ВАЖНО: Теперь выполни команду /reload_config для применения изменений"
        )
        logger.info(f"Admin {message.from_user.id} added {user_id} to whitelist")
    else:
        await message.answer(f"ℹ️ Пользователь {user_id} уже в whitelist")
    
    await state.clear()


@router.callback_query(F.data == "admin_whitelist_remove", IsAdmin())
async def admin_whitelist_remove(callback: CallbackQuery, state: FSMContext):
    """Начать удаление из Whitelist"""
    text = (
        "➖ Удалить из Whitelist\n\n"
        "Отправьте Telegram ID пользователя.\n\n"
        "Отправьте /cancel для отмены"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_whitelist_remove)
    await callback.answer()


@router.message(AdminStates.waiting_for_whitelist_remove, IsAdmin())
async def process_whitelist_remove(message: Message, state: FSMContext):
    """Обработка удаления из Whitelist"""
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    result = await update_env_list("WHITELIST_USER_IDS", user_id, action="remove")
    
    if result:
        await message.answer(
            f"✅ Пользователь {user_id} удалён из Whitelist!\n\n"
            f"⚠️ ВАЖНО: Выполни /reload_config для применения"
        )
        logger.info(f"Admin {message.from_user.id} removed {user_id} from whitelist")
    else:
        await message.answer(f"ℹ️ Пользователь {user_id} не найден в whitelist")
    
    await state.clear()


@router.callback_query(F.data == "admin_blacklist_add", IsAdmin())
async def admin_blacklist_add(callback: CallbackQuery, state: FSMContext):
    """Начать добавление в Blacklist"""
    text = (
        "➕ Добавить в Blacklist\n\n"
        "Отправьте Telegram ID пользователя.\n\n"
        "Отправьте /cancel для отмены"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_blacklist_add)
    await callback.answer()


@router.message(AdminStates.waiting_for_blacklist_add, IsAdmin())
async def process_blacklist_add(message: Message, state: FSMContext):
    """Обработка добавления в Blacklist"""
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    result = await update_env_list("BLACKLIST_USER_IDS", user_id, action="add")
    
    if result:
        await message.answer(
            f"✅ Пользователь {user_id} добавлен в Blacklist!\n\n"
            f"⚠️ ВАЖНО: Выполни /reload_config для применения"
        )
        logger.info(f"Admin {message.from_user.id} added {user_id} to blacklist")
    else:
        await message.answer(f"ℹ️ Пользователь {user_id} уже в blacklist")
    
    await state.clear()


@router.callback_query(F.data == "admin_blacklist_remove", IsAdmin())
async def admin_blacklist_remove(callback: CallbackQuery, state: FSMContext):
    """Начать удаление из Blacklist"""
    text = (
        "➖ Удалить из Blacklist\n\n"
        "Отправьте Telegram ID пользователя.\n\n"
        "Отправьте /cancel для отмены"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_blacklist_remove)
    await callback.answer()


@router.message(AdminStates.waiting_for_blacklist_remove, IsAdmin())
async def process_blacklist_remove(message: Message, state: FSMContext):
    """Обработка удаления из Blacklist"""
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    result = await update_env_list("BLACKLIST_USER_IDS", user_id, action="remove")
    
    if result:
        await message.answer(
            f"✅ Пользователь {user_id} удалён из Blacklist!\n\n"
            f"⚠️ ВАЖНО: Выполни /reload_config для применения"
        )
        logger.info(f"Admin {message.from_user.id} removed {user_id} from blacklist")
    else:
        await message.answer(f"ℹ️ Пользователь {user_id} не найден в blacklist")
    
    await state.clear()


@router.callback_query(F.data == "admin_toggle_whitelist", IsAdmin())
async def admin_toggle_whitelist(callback: CallbackQuery):
    """Переключить Whitelist"""
    env_file = Path(".env")
    
    if not env_file.exists():
        await callback.answer("❌ Файл .env не найден!", show_alert=True)
        return
    
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    found = False
    for i, line in enumerate(lines):
        if line.startswith("ENABLE_WHITELIST="):
            current = line.split("=", 1)[1].strip().lower()
            new_value = "false" if current == "true" else "true"
            lines[i] = f"ENABLE_WHITELIST={new_value}\n"
            found = True
            break
    
    if not found:
        lines.append("ENABLE_WHITELIST=true\n")
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    await callback.answer("✅ Настройка изменена! Выполни /reload_config", show_alert=True)
    await admin_whitelist_menu(callback)


@router.message(Command("reload_config"), IsAdmin())
async def cmd_reload_config(message: Message):
    """Перезагрузка конфигурации"""
    import importlib
    import config
    importlib.reload(config)
    
    await message.answer("✅ Конфигурация перезагружена!\n\nWhitelist/Blacklist обновлены.")
    logger.info(f"Config reloaded by admin {message.from_user.id}")


@router.callback_query(F.data == "admin_broadcast", IsAdmin())
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    text = (
        "📢 РАССЫЛКА СООБЩЕНИЯ\n\n"
        "Отправьте текст сообщения для рассылки ВСЕМ пользователям бота.\n\n"
        "⚠️ Будьте осторожны! Сообщение получат ВСЕ пользователи.\n\n"
        "Отправьте /cancel для отмены"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast, IsAdmin())
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка рассылки - сразу отправляет БЕЗ подтверждения"""
    if message.text == "/cancel":
        await message.answer("❌ Рассылка отменена")
        await state.clear()
        return
    
    broadcast_text = message.text
    
    # Получаем всех пользователей
    users = await user_tracker.get_all_users()
    
    if not users:
        await message.answer("❌ Нет пользователей для рассылки")
        await state.clear()
        return
    
    # Начинаем рассылку СРАЗУ
    status_msg = await message.answer(f"📤 Начинаю рассылку для {len(users)} пользователей...")
    
    success = 0
    failed = 0
    
    for user in users:
        user_id = user['user_id']
        try:
            await message.bot.send_message(user_id, broadcast_text)
            success += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Failed to send broadcast to {user_id}: {e}")
    
    # Результат
    result_text = (
        f"✅ Рассылка завершена!\n\n"
        f"Успешно: {success}\n"
        f"Ошибок: {failed}\n"
        f"Всего: {len(users)}"
    )
    
    await status_msg.edit_text(result_text)
    await state.clear()
    
    logger.info(f"Broadcast completed by admin {message.from_user.id}: {success} success, {failed} failed")


@router.callback_query(F.data == "admin_settings", IsAdmin())
async def admin_settings(callback: CallbackQuery):
    """Меню настроек"""
    text = "⚙️ НАСТРОЙКИ БОТА\n\nВыберите действие:"
    
    await callback.message.edit_text(text, reply_markup=get_settings_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_images_stats", IsAdmin())
async def admin_images_stats(callback: CallbackQuery):
    """Статистика по картинкам"""
    from media.image_manager import ImageManager
    
    img_manager = ImageManager()
    stats = img_manager.get_statistics()
    
    text = "🖼 СТАТИСТИКА КАРТИНОК\n\n"
    
    total = sum(stats.values())
    text += f"Всего: {total}\n\n"
    
    for mood, count in stats.items():
        text += f"• {mood}: {count}\n"
    
    if total == 0:
        text += "\n⚠️ Нет картинок!\nДобавьте в assets/mahiro/"
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_settings"))
    await callback.answer()


async def update_env_list(key: str, user_id: int, action: str) -> bool:
    """Обновляет список в .env файле"""
    env_file = Path(".env")
    
    if not env_file.exists():
        return False
    
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    line_index = None
    current_ids = []
    
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            line_index = i
            ids_str = line.split("=", 1)[1].strip()
            if ids_str:
                current_ids = [int(x) for x in ids_str.split(",") if x.strip()]
            break
    
    if action == "add":
        if user_id in current_ids:
            return False
        current_ids.append(user_id)
    elif action == "remove":
        if user_id not in current_ids:
            return False
        current_ids.remove(user_id)
    
    new_ids_str = ",".join(map(str, current_ids))
    
    if line_index is not None:
        lines[line_index] = f"{key}={new_ids_str}\n"
    else:
        lines.append(f"{key}={new_ids_str}\n")
    
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True


# ========== НОВЫЕ РАСШИРЕННЫЕ ФУНКЦИИ ==========

@router.callback_query(F.data == "admin_detailed_stats", IsAdmin())
async def admin_detailed_stats(callback: CallbackQuery):
    """Подробная статистика"""
    from utils.user_tracker import UserTracker
    from memory.mood_system import MoodSystem
    
    tracker = UserTracker()
    mood_system = MoodSystem()
    
    users = await tracker.get_all_users()
    
    # Анализ по дням недели
    from datetime import datetime
    import collections
    
    weekday_activity = collections.Counter()
    hour_activity = collections.Counter()
    
    for user in users:
        last_seen = datetime.fromisoformat(user.get('last_seen', datetime.now().isoformat()))
        weekday_activity[last_seen.strftime("%A")] += 1
        hour_activity[last_seen.hour] += 1
    
    # Топ-5 активных часов
    top_hours = sorted(hour_activity.items(), key=lambda x: x[1], reverse=True)[:5]
    
    text = "📊 ПОДРОБНАЯ СТАТИСТИКА\n\n"
    text += f"📅 Активность по дням:\n"
    for day, count in weekday_activity.most_common(7):
        text += f"  {day}: {count}\n"
    
    text += f"\n⏰ Топ-5 активных часов:\n"
    for hour, count in top_hours:
        text += f"  {hour}:00 - {count} польз.\n"
    
    text += f"\n💬 Средняя длина диалога: "
    avg_messages = sum(u.get('message_count', 0) for u in users) / max(len(users), 1)
    text += f"{avg_messages:.1f} сообщ.\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_settings"))
    await callback.answer()


@router.callback_query(F.data == "admin_export_data", IsAdmin())
async def admin_export_data(callback: CallbackQuery):
    """Экспорт данных"""
    keyboard = [
        [InlineKeyboardButton(text="💾 Полный бэкап (ZIP)", callback_data="export_full")],
        [InlineKeyboardButton(text="📊 CSV пользователей", callback_data="export_csv")],
        [InlineKeyboardButton(text="📈 JSON статистика", callback_data="export_json")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_settings")],
    ]
    
    text = (
        "💾 ЭКСПОРТ ДАННЫХ\n\n"
        "Выберите формат экспорта:"
    )
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data == "export_full", IsAdmin())
async def export_full_backup(callback: CallbackQuery):
    """Полный бэкап"""
    from utils.database_export import DatabaseExporter
    
    await callback.answer("⏳ Создаю бэкап...", show_alert=False)
    
    exporter = DatabaseExporter()
    zip_path = await exporter.export_all()
    
    if zip_path:
        try:
            from aiogram.types import FSInputFile
            file = FSInputFile(zip_path)
            await callback.message.answer_document(
                file,
                caption=f"💾 Полный бэкап базы данных\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            await callback.answer("✅ Бэкап создан!", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to send backup: {e}")
            await callback.answer("❌ Ошибка отправки файла", show_alert=True)
    else:
        await callback.answer("❌ Ошибка создания бэкапа", show_alert=True)


@router.callback_query(F.data == "export_csv", IsAdmin())
async def export_users_csv(callback: CallbackQuery):
    """Экспорт пользователей в CSV"""
    from utils.database_export import DatabaseExporter
    
    await callback.answer("⏳ Создаю CSV...", show_alert=False)
    
    exporter = DatabaseExporter()
    csv_path = await exporter.export_users_csv()
    
    if csv_path:
        try:
            from aiogram.types import FSInputFile
            file = FSInputFile(csv_path)
            await callback.message.answer_document(
                file,
                caption=f"📊 Экспорт пользователей\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            await callback.answer("✅ CSV создан!", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to send CSV: {e}")
            await callback.answer("❌ Ошибка отправки файла", show_alert=True)
    else:
        await callback.answer("❌ Ошибка создания CSV", show_alert=True)


@router.callback_query(F.data == "export_json", IsAdmin())
async def export_statistics_json(callback: CallbackQuery):
    """Экспорт статистики в JSON"""
    from utils.database_export import DatabaseExporter
    
    await callback.answer("⏳ Создаю JSON...", show_alert=False)
    
    exporter = DatabaseExporter()
    json_path = await exporter.export_statistics_json()
    
    if json_path:
        try:
            from aiogram.types import FSInputFile
            file = FSInputFile(json_path)
            await callback.message.answer_document(
                file,
                caption=f"📈 Экспорт статистики\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            await callback.answer("✅ JSON создан!", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to send JSON: {e}")
            await callback.answer("❌ Ошибка отправки файла", show_alert=True)
    else:
        await callback.answer("❌ Ошибка создания JSON", show_alert=True)


@router.callback_query(F.data == "admin_mass_operations", IsAdmin())
async def admin_mass_operations(callback: CallbackQuery):
    """Массовые операции"""
    keyboard = [
        [InlineKeyboardButton(text="🗑 Очистить неактивных (30д)", callback_data="mass_cleanup_inactive")],
        [InlineKeyboardButton(text="📊 Пересчитать статистику", callback_data="mass_recalc_stats")],
        [InlineKeyboardButton(text="🔄 Сброс доверия всех", callback_data="mass_reset_trust")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_settings")],
    ]
    
    text = (
        "⚙️ МАССОВЫЕ ОПЕРАЦИИ\n\n"
        "⚠️ Осторожно! Эти действия необратимы!\n\n"
        "Выберите операцию:"
    )
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data == "mass_cleanup_inactive", IsAdmin())
async def mass_cleanup_inactive(callback: CallbackQuery):
    """Очистка неактивных пользователей"""
    from datetime import datetime, timedelta
    
    users = await user_tracker.get_all_users()
    cutoff_date = datetime.now() - timedelta(days=30)
    
    deleted_count = 0
    
    for user in users:
        last_seen = datetime.fromisoformat(user.get('last_seen', datetime.now().isoformat()))
        if last_seen < cutoff_date:
            user_id = user['user_id']
            # Удаляем файлы пользователя
            user_file = Path(f"data/user_{user_id}.json")
            if user_file.exists():
                user_file.unlink()
                deleted_count += 1
    
    await callback.answer(f"✅ Удалено {deleted_count} неактивных пользователей", show_alert=True)
    await admin_mass_operations(callback)


@router.callback_query(F.data == "admin_notifications_toggle", IsAdmin())
async def admin_notifications_toggle(callback: CallbackQuery):
    """Переключение уведомлений"""
    from utils.admin_notifications import admin_notifier
    
    if admin_notifier.enabled:
        admin_notifier.disable()
        status = "ВЫКЛЮЧЕНЫ"
    else:
        admin_notifier.enable()
        status = "ВКЛЮЧЕНЫ"
    
    await callback.answer(f"🔔 Уведомления {status}", show_alert=True)
    await admin_settings(callback)


@router.message(Command("logs"), IsAdmin())
async def cmd_logs(message: Message):
    """Показать последние логи"""
    log_file = Path("mahiro_bot.log")
    
    if not log_file.exists():
        await message.answer("📋 Файл логов не найден")
        return
    
    # Читаем последние 50 строк
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        last_lines = lines[-50:]
    
    log_text = "📋 ПОСЛЕДНИЕ ЛОГИ:\n\n" + "".join(last_lines[-20:])
    
    # Если слишком длинно, отправляем файлом
    if len(log_text) > 4000:
        from aiogram.types import FSInputFile
        file = FSInputFile(log_file)
        await message.answer_document(file, caption="📋 Полный лог файл")
    else:
        await message.answer(f"```\n{log_text}\n```", parse_mode="Markdown")


@router.message(Command("system"), IsAdmin())
async def cmd_system(message: Message):
    """Системная информация"""
    import psutil
    import sys
    
    # CPU и память
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    text = f"""💻 СИСТЕМНАЯ ИНФОРМАЦИЯ

🐍 Python: {sys.version.split()[0]}
💾 Память: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)
🔥 CPU: {cpu_percent}%

📂 Размер базы данных:
"""
    
    # Размер data/
    data_dir = Path("data")
    if data_dir.exists():
        total_size = sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file())
        text += f"  {total_size // 1024 // 1024}MB\n"
    
    # Uptime бота
    from utils.statistics import Statistics
    stats = Statistics()
    bot_stats = await stats.get_stats()
    start_time = datetime.fromisoformat(bot_stats["start_time"])
    uptime = datetime.now() - start_time
    
    text += f"\n⏱ Uptime: {uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м"
    
    await message.answer(text)


# ========== УПРАВЛЕНИЕ ДОНАТАМИ ==========

@router.callback_query(F.data == "admin_donations", IsAdmin())
async def admin_donations(callback: CallbackQuery):
    """Меню донатов"""
    from utils.donations import donation_system
    
    stats = await donation_system.get_statistics()
    
    text = f"""💰 ДОНАТЫ

📊 Статистика:
• Всего донатов: {stats['total_donations']}
• Активных: {stats['active_donations']}
• Возвращено: {stats['refunded_donations']}

⭐ Звёзды:
• Получено: {stats['total_stars_donated']}
• Возвращено: {stats['total_stars_refunded']}

👥 Уникальных донатеров: {stats['unique_donors']}
"""
    
    keyboard = [
        [InlineKeyboardButton(text="🏆 Топ донатеров", callback_data="admin_top_donors")],
        [InlineKeyboardButton(text="📜 Все донаты", callback_data="admin_all_donations")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data == "admin_top_donors", IsAdmin())
async def admin_top_donors(callback: CallbackQuery):
    """Топ донатеров (админ)"""
    from utils.donations import donation_system
    
    top_donors = await donation_system.get_top_donors(20)
    
    if not top_donors:
        text = "🏆 ТОП ДОНАТЕРОВ\n\nПока нет донатов"
    else:
        text = f"🏆 ТОП ДОНАТЕРОВ ({len(top_donors)})\n\n"
        
        for i, donor in enumerate(top_donors, 1):
            name = donor['first_name']
            username = donor['username']
            stars = donor['total_stars']
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            text += f"{medal} {name} (@{username})\n"
            text += f"     ⭐ {stars} звёзд\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_donations"))
    await callback.answer()


@router.callback_query(F.data == "admin_all_donations", IsAdmin())
async def admin_all_donations(callback: CallbackQuery):
    """Все донаты (админ)"""
    from utils.donations import donation_system
    
    donations = await donation_system.get_all_donations()
    
    if not donations:
        text = "📜 СПИСОК ДОНАТОВ\n\nПока нет донатов"
    else:
        # Последние 15
        recent = sorted(donations, key=lambda x: x['timestamp'], reverse=True)[:15]
        
        text = f"📜 ДОНАТЫ (последние 15 из {len(donations)})\n\n"
        
        for d in recent:
            status = "❌ ВОЗВРАТ" if d.get('refunded') else "✅"
            name = d['first_name']
            stars = d['stars']
            date = datetime.fromisoformat(d['timestamp']).strftime("%d.%m %H:%M")
            
            text += f"{status} {name} — ⭐ {stars}\n"
            text += f"   {date}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_button("admin_donations"))
    await callback.answer()