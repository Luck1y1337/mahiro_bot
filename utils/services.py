from ai.mistral_client import MistralClient
from memory.storage import MemoryStorage
from memory.trust_system import TrustSystem
from memory.mood_system import MoodSystem, MessageCounter
from memory.long_term_memory import LongTermMemory
from media.image_manager import ImageManager
from utils.statistics import Statistics
from utils.rate_limiter import RateLimiter
from utils.user_tracker import UserTracker
from ai.triggers import TriggerSystem

# Глобальные синглтоны сервисов
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
