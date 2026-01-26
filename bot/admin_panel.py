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
        [InlineKeyboardButton(text="🔐 Whitelist", callback_data="admin_whitelist_menu")],
        [InlineKeyboardButton(text="🚫 Blacklist", callback_data="admin_blacklist_menu")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_whitelist_menu() -> InlineKeyboardMarkup:
    """Меню Whitelist"""
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS

    status = "✅ Вкл" if ENABLE_WHITELIST else "❌ Выкл"

    keyboard = [
        [InlineKeyboardButton(text=f"🔐 Whitelist: {status}", callback_data="admin_toggle_whitelist")],
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="admin_whitelist_add")],
        [InlineKeyboardButton(text="➖ Удалить пользователя", callback_data="admin_whitelist_remove")],
        [InlineKeyboardButton(text=f"📋 Список ({len(WHITELIST_USER_IDS)})", callback_data="admin_list_whitelist")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_blacklist_menu() -> InlineKeyboardMarkup:
    """Меню Blacklist"""
    from config import BLACKLIST_USER_IDS

    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить в Blacklist", callback_data="admin_blacklist_add")],
        [InlineKeyboardButton(text="➖ Удалить из Blacklist", callback_data="admin_blacklist_remove")],
        [InlineKeyboardButton(text=f"📋 Список ({len(BLACKLIST_USER_IDS)})", callback_data="admin_list_blacklist")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_menu() -> InlineKeyboardMarkup:
    """Меню настроек"""
    keyboard = [
        [InlineKeyboardButton(text="🖼 Статистика картинок", callback_data="admin_images_stats")],
        [InlineKeyboardButton(text="🗑 Очистка данных", callback_data="admin_cleanup")],
        [InlineKeyboardButton(text="💾 Экспорт данных", callback_data="admin_export")],
        [InlineKeyboardButton(text="📊 Подробная статистика", callback_data="admin_detailed_stats")],
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
        "🎛 **АДМИН-ПАНЕЛЬ МАХИРО**\n\n"
        "Добро пожаловать в панель управления!\n"
        "Выберите нужный раздел:"
    )

    await message.answer(text, reply_markup=get_main_admin_menu(), parse_mode="Markdown")


@router.callback_query(F.data == "admin_main", IsAdmin())
async def admin_main(callback: CallbackQuery):
    """Главное меню"""
    text = (
        "🎛 **АДМИН-ПАНЕЛЬ МАХИРО**\n\n"
        "Выберите нужный раздел:"
    )

    try:
        await callback.message.edit_text(text, reply_markup=get_main_admin_menu(), parse_mode="Markdown")
    except Exception as e:
        # Игнорируем ошибку "message is not modified"
        if "message is not modified" not in str(e):
            logger.error(f"Ошибка редактирования сообщения: {e}")
            raise

    await callback.answer()


@router.callback_query(F.data == "admin_refresh", IsAdmin())
async def admin_refresh(callback: CallbackQuery):
    """Обновление панели"""
    try:
        await callback.answer("✅ Панель обновлена", show_alert=False)
        await admin_main(callback)
    except Exception as e:
        # Игнорируем ошибку "message is not modified"
        if "message is not modified" in str(e):
            await callback.answer("Панель уже актуальна", show_alert=False)
        else:
            logger.error(f"Ошибка обновления панели: {e}")
            await callback.answer("❌ Ошибка обновления", show_alert=True)


@router.callback_query(F.data == "admin_stats", IsAdmin())
async def admin_stats(callback: CallbackQuery):
    """Показать статистику"""
    bot_stats = await statistics.get_stats()
    user_stats = await user_tracker.get_statistics()

    start_time = datetime.fromisoformat(bot_stats["start_time"])
    uptime = datetime.now() - start_time
    uptime_str = f"{uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м"

    text = f"""📊 **СТАТИСТИКА БОТА**

⏱ Время работы: {uptime_str}

**Пользователи:**
• 👥 Всего: {user_stats['total_users']}
• 🟢 Активных (7 дней): {user_stats['active_7d']}
• 🟢 Активных (30 дней): {user_stats['active_30d']}

**Сообщения:**
• 💬 Всего: {user_stats['total_messages']}
• ✅ Обработано: {user_stats['successful_messages']}
• 🚫 Заблокировано: {user_stats['blocked_messages']}

**Система:**
• 🖼 Картинок отправлено: {bot_stats['images_sent']}
• ❌ Ошибок: {bot_stats['errors']}
"""

    keyboard = [[InlineKeyboardButton(text="« Назад", callback_data="admin_main")]]

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users_list", IsAdmin())
async def admin_users_list(callback: CallbackQuery):
    """Список всех пользователей"""
    users = await user_tracker.get_all_users()

    if not users:
        text = "📭 **Пользователей пока нет**"
    else:
        # Сортируем по последней активности
        users.sort(key=lambda x: x.get("last_seen", ""), reverse=True)

        text = f"👥 **ВСЕ ПОЛЬЗОВАТЕЛИ ({len(users)})**\n\n"

        # Показываем последних 20
        for user in users[:20]:
            user_id = user['user_id']
            username = user.get('username', 'нет username')
            first_name = user.get('first_name', 'Аноним')
            msg_count = user.get('message_count', 0)
            blocked = user.get('blocked_messages', 0)

            # Экранируем спецсимволы для Markdown
            def escape_md(text):
                """Экранирует спецсимволы Markdown"""
                if not text:
                    return text
                # Экранируем: _ * [ ] ( ) ~ ` > # + - = | { } . !
                special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.',
                                 '!']
                for char in special_chars:
                    text = text.replace(char, f'\\{char}')
                return text

            first_name_safe = escape_md(first_name)
            username_safe = escape_md(username)

            # Статус
            from config import ADMIN_USER_IDS, WHITELIST_USER_IDS, BLACKLIST_USER_IDS
            status = []
            if user_id in ADMIN_USER_IDS:
                status.append("👑")
            if user_id in WHITELIST_USER_IDS:
                status.append("✅")
            if user_id in BLACKLIST_USER_IDS:
                status.append("🚫")

            status_str = " ".join(status) if status else "👤"

            text += f"{status_str} **{first_name_safe}** (@{username_safe})\n"
            text += f"   ID: `{user_id}` | 💬 {msg_count}"
            if blocked > 0:
                text += f" | 🚫 {blocked}"
            text += "\n\n"

        if len(users) > 20:
            text += f"\n_\\.\\.\\.и ещё {len(users) - 20} пользователей_"

    keyboard = [
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_user_search")],
        [InlineKeyboardButton(text="🚫 Заблокированные попытки", callback_data="admin_blocked_users")],
        [InlineKeyboardButton(text="« Назад", callback_data="admin_main")],
    ]

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_blocked_users", IsAdmin())
async def admin_blocked_users(callback: CallbackQuery):
    """Пользователи с заблокированными сообщениями"""
    blocked = await user_tracker.get_blocked_users()

    if not blocked:
        text = "✅ **Нет заблокированных попыток**"
    else:
        text = f"🚫 **ЗАБЛОКИРОВАННЫЕ ПОПЫТКИ ({len(blocked)})**\n\n"

        # Функция экранирования
        def escape_md(text):
            if not text:
                return text
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = text.replace(char, f'\\{char}')
            return text

        for user in blocked[:15]:
            user_id = user['user_id']
            username = escape_md(user.get('username', 'нет username'))
            first_name = escape_md(user.get('first_name', 'Аноним'))
            blocked_count = user.get('blocked_messages', 0)

            text += f"👤 **{first_name}** (@{username})\n"
            text += f"   ID: `{user_id}` | 🚫 {blocked_count} заблок\\.\n\n"

        if len(blocked) > 15:
            text += f"\n_\\.\\.\\.и ещё {len(blocked) - 15}_"

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button("admin_users_list"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_list_whitelist", IsAdmin())
async def admin_list_whitelist(callback: CallbackQuery):
    """Показать список Whitelist"""
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS

    if not ENABLE_WHITELIST:
        text = "❌ **Whitelist выключен**\n\nВсе пользователи имеют доступ к боту\\."
    elif not WHITELIST_USER_IDS:
        text = "⚠️ **Whitelist пуст**\n\nТолько админы могут пользоваться ботом\\."
    else:
        text = f"📋 **WHITELIST ({len(WHITELIST_USER_IDS)} польз\\.)**\n\n"

        def escape_md(text):
            if not text:
                return text
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = text.replace(char, f'\\{char}')
            return text

        # Получаем инфо о пользователях
        for user_id in WHITELIST_USER_IDS:
            user_info = await user_tracker.get_user_info(user_id)
            if user_info:
                name = escape_md(user_info.get('first_name', 'Неизвестно'))
                username = escape_md(user_info.get('username', 'нет'))
                text += f"• **{name}** (@{username})\n   ID: `{user_id}`\n\n"
            else:
                text += f"• ID: `{user_id}` _\\(нет данных\\)_\n\n"

    await callback.message.edit_text(text, reply_markup=get_back_button("admin_whitelist_menu"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_list_blacklist", IsAdmin())
async def admin_list_blacklist(callback: CallbackQuery):
    """Показать список Blacklist"""
    from config import BLACKLIST_USER_IDS

    if not BLACKLIST_USER_IDS:
        text = "✅ **Blacklist пуст**\n\nНет заблокированных пользователей\\."
    else:
        text = f"🚫 **BLACKLIST ({len(BLACKLIST_USER_IDS)} польз\\.)**\n\n"

        def escape_md(text):
            if not text:
                return text
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in special_chars:
                text = text.replace(char, f'\\{char}')
            return text

        for user_id in BLACKLIST_USER_IDS:
            user_info = await user_tracker.get_user_info(user_id)
            if user_info:
                name = escape_md(user_info.get('first_name', 'Неизвестно'))
                username = escape_md(user_info.get('username', 'нет'))
                text += f"• **{name}** (@{username})\n   ID: `{user_id}`\n\n"
            else:
                text += f"• ID: `{user_id}` _\\(нет данных\\)_\n\n"

    await callback.message.edit_text(text, reply_markup=get_back_button("admin_blacklist_menu"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_list_whitelist", IsAdmin())
async def admin_list_whitelist(callback: CallbackQuery):
    """Показать список Whitelist"""
    from config import ENABLE_WHITELIST, WHITELIST_USER_IDS

    if not ENABLE_WHITELIST:
        text = "❌ **Whitelist выключен**\n\nВсе пользователи имеют доступ к боту."
    elif not WHITELIST_USER_IDS:
        text = "⚠️ **Whitelist пуст**\n\nТолько админы могут пользоваться ботом."
    else:
        text = f"📋 **WHITELIST ({len(WHITELIST_USER_IDS)} польз.)**\n\n"

        # Получаем инфо о пользователях
        for user_id in WHITELIST_USER_IDS:
            user_info = await user_tracker.get_user_info(user_id)
            if user_info:
                name = user_info.get('first_name', 'Неизвестно')
                username = user_info.get('username', 'нет')
                text += f"• **{name}** (@{username})\n   ID: `{user_id}`\n\n"
            else:
                text += f"• ID: `{user_id}` _(нет данных)_\n\n"

    await callback.message.edit_text(text, reply_markup=get_back_button("admin_whitelist_menu"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_list_blacklist", IsAdmin())
async def admin_list_blacklist(callback: CallbackQuery):
    """Показать список Blacklist"""
    from config import BLACKLIST_USER_IDS

    if not BLACKLIST_USER_IDS:
        text = "✅ **Blacklist пуст**\n\nНет заблокированных пользователей."
    else:
        text = f"🚫 **BLACKLIST ({len(BLACKLIST_USER_IDS)} польз.)**\n\n"

        for user_id in BLACKLIST_USER_IDS:
            user_info = await user_tracker.get_user_info(user_id)
            if user_info:
                name = user_info.get('first_name', 'Неизвестно')
                username = user_info.get('username', 'нет')
                text += f"• **{name}** (@{username})\n   ID: `{user_id}`\n\n"
            else:
                text += f"• ID: `{user_id}` _(нет данных)_\n\n"

    await callback.message.edit_text(text, reply_markup=get_back_button("admin_blacklist_menu"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_whitelist_add", IsAdmin())
async def admin_whitelist_add(callback: CallbackQuery, state: FSMContext):
    """Начать добавление в Whitelist"""
    text = (
        "➕ **Добавить в Whitelist**\n\n"
        "Отправьте Telegram ID пользователя.\n\n"
        "💡 Узнать ID: @userinfobot\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="Markdown")
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

    # Обновляем .env
    result = await update_env_list("WHITELIST_USER_IDS", user_id, action="add")

    if result:
        await message.answer(
            f"✅ Пользователь `{user_id}` добавлен в Whitelist!\n\n"
            f"⚠️ Перезапустите бота для применения изменений.",
            parse_mode="Markdown"
        )
        logger.info(f"Admin {message.from_user.id} added {user_id} to whitelist")
    else:
        await message.answer("❌ Ошибка при добавлении!")

    await state.clear()


@router.callback_query(F.data == "admin_whitelist_remove", IsAdmin())
async def admin_whitelist_remove(callback: CallbackQuery, state: FSMContext):
    """Начать удаление из Whitelist"""
    text = (
        "➖ **Удалить из Whitelist**\n\n"
        "Отправьте Telegram ID пользователя.\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="Markdown")
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
            f"✅ Пользователь `{user_id}` удалён из Whitelist!\n\n"
            f"⚠️ Перезапустите бота.",
            parse_mode="Markdown"
        )
        logger.info(f"Admin {message.from_user.id} removed {user_id} from whitelist")
    else:
        await message.answer("❌ Ошибка при удалении!")

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

    await callback.answer("✅ Настройка изменена! Перезапустите бота", show_alert=True)
    await admin_whitelist_menu(callback)


@router.callback_query(F.data == "admin_settings", IsAdmin())
async def admin_settings(callback: CallbackQuery):
    """Меню настроек"""
    text = "⚙️ **НАСТРОЙКИ БОТА**\n\nВыберите действие:"

    await callback.message.edit_text(text, reply_markup=get_settings_menu(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_images_stats", IsAdmin())
async def admin_images_stats(callback: CallbackQuery):
    """Статистика по картинкам"""
    from media.image_manager import ImageManager

    img_manager = ImageManager()
    stats = img_manager.get_statistics()

    text = "🖼 **СТАТИСТИКА КАРТИНОК**\n\n"

    total = sum(stats.values())
    text += f"Всего: {total}\n\n"

    for mood, count in stats.items():
        text += f"• {mood}: {count}\n"

    if total == 0:
        text += "\n⚠️ Нет картинок!\nДобавьте в `assets/mahiro/`"

    await callback.message.edit_text(text, reply_markup=get_back_button("admin_settings"), parse_mode="Markdown")
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