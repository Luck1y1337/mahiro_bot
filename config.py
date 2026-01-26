import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Mistral AI
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = "mistral-small-latest"  # быстрая и дешёвая

# Настройки памяти
MAX_HISTORY_MESSAGES = 20  # сколько сообщений помнить
TRUST_INCREMENT = 0.05     # рост доверия за сообщение
MAX_TRUST = 1.0            # максимальное доверие

# Настройки генерации
TEMPERATURE = 0.85         # креативность (0.7-0.9 для персонажа)
MAX_TOKENS = 500           # макс длина ответа