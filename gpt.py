"""
Модуль для работы с GPT-4 API
"""
import asyncio
import logging
from typing import AsyncGenerator
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, read_prompt, MAX_TOKENS

logger = logging.getLogger(__name__)

# Инициализируем клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def get_gpt_response(text: str, user_name: str = "Пользователь") -> str:
    """
    Получает ответ от GPT-4 на основе пользовательского текста
    
    Args:
        text: Текст пользователя для обработки
        user_name: Имя пользователя для персонализации
        
    Returns:
        str: Ответ от GPT-4
        
    Raises:
        ValueError: При ошибках API или обработки
    """
    try:
        # Читаем текущий системный промпт
        system_prompt = read_prompt()
        
        # Формируем сообщения для GPT
        messages = [
            {
                "role": "system", 
                "content": f"{system_prompt}\n\nОбращайся к пользователю по имени: {user_name}"
            },
            {
                "role": "user", 
                "content": text
            }
        ]
        
        # Отправляем запрос к GPT-4
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=MAX_TOKENS,  # Ограничиваем длину ответа (настраивается в .env)
            temperature=0.7,  # Немного креативности, но не слишком много
            presence_penalty=0.1,  # Избегаем повторений
            frequency_penalty=0.1
        )
        
        gpt_text = response.choices[0].message.content.strip()
        
        if not gpt_text:
            raise ValueError("GPT вернул пустой ответ")
        
        logger.info(f"GPT ответ получен: {len(gpt_text)} символов")
        return gpt_text
        
    except Exception as e:
        logger.error(f"Ошибка GPT: {e}")
        
        if "insufficient_quota" in str(e).lower() or "quota" in str(e).lower():
            raise ValueError("Превышен лимит использования GPT. Обратитесь к администратору.")
        elif "rate limit" in str(e).lower():
            raise ValueError("Слишком много запросов к GPT. Попробуйте через минуту.")
        elif "invalid" in str(e).lower():
            raise ValueError("Ошибка обработки запроса. Попробуйте переформулировать.")
        else:
            raise ValueError("Временная ошибка GPT. Попробуйте ещё раз.")

async def get_gpt_response_stream(text: str, user_name: str = "Пользователь") -> AsyncGenerator[str, None]:
    """
    Получает потоковый ответ от GPT-4 (для будущего использования)
    
    Args:
        text: Текст пользователя для обработки
        user_name: Имя пользователя для персонализации
        
    Yields:
        str: Части ответа от GPT-4
    """
    try:
        # Читаем текущий системный промпт
        system_prompt = read_prompt()
        
        # Формируем сообщения для GPT
        messages = [
            {
                "role": "system", 
                "content": f"{system_prompt}\n\nОбращайся к пользователю по имени: {user_name}"
            },
            {
                "role": "user", 
                "content": text
            }
        ]
        
        # Отправляем потоковый запрос к GPT-4
        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            presence_penalty=0.1,
            frequency_penalty=0.1,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
                
    except Exception as e:
        logger.error(f"Ошибка потокового GPT: {e}")
        yield "Извини, произошла ошибка при генерации ответа."

def validate_user_input(text: str) -> bool:
    """
    Проверяет корректн��сть пользовательского ввода
    
    Args:
        text: Текст для проверки
        
    Returns:
        bool: True если текст корректен
    """
    if not text or not text.strip():
        return False
    
    # Проверяем минимальную длину
    if len(text.strip()) < 3:
        return False
    
    # Проверяем максимальную длину (для защиты от спама)
    if len(text) > 5000:
        return False
    
    return True