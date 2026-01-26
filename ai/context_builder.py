from datetime import datetime
from typing import List, Dict


def get_time_of_day() -> str:
    """Определяет время суток"""
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return "утро"
    elif 12 <= hour < 18:
        return "день"
    elif 18 <= hour < 23:
        return "вечер"
    else:
        return "ночь"


def format_history_for_context(history: List[Dict[str, str]], max_messages: int = 10) -> List[Dict[str, str]]:
    """
    Форматирует историю для передачи в Mistral API

    Args:
        history: список сообщений [{"role": "user"/"assistant", "content": "..."}]
        max_messages: сколько последних сообщений брать

    Returns:
        Отформатированная история для API
    """
    # Берём последние N сообщений
    recent_history = history[-max_messages:] if len(history) > max_messages else history

    return recent_history


def build_user_message(text: str, context_info: str = "") -> str:
    """
    Строит сообщение пользователя с дополнительным контекстом

    Args:
        text: текст сообщения
        context_info: дополнительная информация (например, "пользователь впервые пишет")
    """
    if context_info:
        return f"{text}\n\n[Контекст: {context_info}]"
    return text