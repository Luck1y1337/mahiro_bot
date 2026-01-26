from mistralai import Mistral
from typing import List, Dict, Optional
import logging

from config import MISTRAL_API_KEY, MISTRAL_MODEL, TEMPERATURE, MAX_TOKENS

logger = logging.getLogger(__name__)


class MistralClient:
    def __init__(self):
        self.client = Mistral(api_key=MISTRAL_API_KEY)
        self.model = MISTRAL_MODEL

    async def generate_response(
            self,
            system_prompt: str,
            history: List[Dict[str, str]],
            user_message: str
    ) -> Optional[str]:
        """
        Генерирует ответ Махиро

        Args:
            system_prompt: системный промпт с контекстом
            history: история диалога
            user_message: новое сообщение пользователя

        Returns:
            Ответ Махиро или None при ошибке
        """
        try:
            # Формируем сообщения для API
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # Добавляем историю
            messages.extend(history)

            # Добавляем новое сообщение пользователя
            messages.append({"role": "user", "content": user_message})

            # Вызываем API
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )

            # Извлекаем ответ
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content

            logger.error("Пустой ответ от Mistral API")
            return None

        except Exception as e:
            logger.error(f"Ошибка при обращении к Mistral API: {e}")
            return None