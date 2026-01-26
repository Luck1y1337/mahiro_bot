import os
from dotenv import load_dotenv

load_dotenv()

# ========== Telegram ==========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# ========== Mistral AI ==========
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = "mistral-small-latest"

# ========== Память ==========
MAX_HISTORY_MESSAGES = 20
TRUST_INCREMENT = 0.05
MAX_TRUST = 1.0

# ========== Генерация ==========
TEMPERATURE = 0.85
MAX_TOKENS = 500

# ========== Rate Limiting ==========
MAX_MESSAGES_PER_MINUTE = 10
MAX_MESSAGES_PER_DAY = 100
COOLDOWN_SECONDS = 2

# ========== Whitelist/Blacklist ==========
ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x]
BLACKLIST_USER_IDS = [int(x) for x in os.getenv("BLACKLIST_USER_IDS", "").split(",") if x]

# ========== Whitelist (белый список) ==========
ENABLE_WHITELIST = os.getenv("ENABLE_WHITELIST", "false").lower() == "true"
WHITELIST_USER_IDS = [int(x) for x in os.getenv("WHITELIST_USER_IDS", "").split(",") if x]

# ========== Долгосрочная память ==========
ENABLE_LONG_TERM_MEMORY = True
MAX_FACTS_PER_USER = 50

# ========== Картинки ==========
IMAGES_ENABLED = True
IMAGES_FOLDER = "assets/mahiro"
IMAGE_SEND_CHANCE = 0.15

# ========== Статистика ==========
ENABLE_STATISTICS = True

# ========== Языки ==========
DEFAULT_LANGUAGE = "ru"
SUPPORTED_LANGUAGES = ["ru", "en"]