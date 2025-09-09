"""
Модуль для преобразования текста в речь с использованием OpenAI TTS
"""
import asyncio
import logging
from pathlib import Path
from openai import AsyncOpenAI

from config import OPENAI_API_KEY
from utils import create_temp_file, cleanup_temp_file
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # Изменили на DEBUG для более подробных логов
    handlers=[
        logging.FileHandler('session.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
#logger = logging.getLogger(__name__)

# Инициализируем клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def text_to_speech(text: str, output_path: Path = None) -> Path:
    """
    Преобразует текст в речь с использованием OpenAI TTS
    
    Args:
        text: Текст для озвучивания
        output_path: Путь для сохранения аудиофайла (если не указан, создается временный)
        
    Returns:
        Path: Путь к созданному аудиофайлу
        
    Raises:
        ValueError: При ошибках генерации или обработки
    """
    if not output_path:
        output_path = create_temp_file('.mp3')
    
    try:
        # Проверяем длину текста
        if len(text) > 4096:
            # OpenAI TTS имеет лимит на длину текста
            text = text[:4090] + "..."
            #logger.warning("Текст обрезан до лимита TTS")
        
        if not text.strip():
            raise ValueError("Пустой текст для озвучивания")
        
        # Генерируем речь
        response = await client.audio.speech.create(
            model="tts-1",
            voice="onyx",  # Используем голос onyx как указано в ТЗ
            input=text,
            response_format="mp3"
        )
        
        # Сохраняем аудиофайл
        response_bytes = response.read()
        with open(output_path, 'wb') as audio_file:
            audio_file.write(response_bytes)
        
        # Проверяем, что файл создан и не пустой
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ValueError("Не удалось создать аудиофайл")
        
        #logger.info(f"TTS успешно: {len(text)} символов -> {output_path}")
        return output_path
        
    except Exception as e:
        #logger.error(f"Ошибка TTS: {e}")
        
        # Очищаем файл при ошибке
        if output_path and output_path.exists():
            cleanup_temp_file(output_path)
        
        if "rate limit" in str(e).lower():
            raise ValueError("Слишком много запросов к TTS. Попробуйте через минуту.")
        elif "quota" in str(e).lower():
            raise ValueError("Превышен лимит использования TTS. Обратитесь к администратору.")
        elif "invalid" in str(e).lower():
            raise ValueError("Ошибка обработки текста для озвучивания.")
        else:
            raise ValueError("Временная ошибка TTS. Попробуйте ещё раз.", str(e))

async def validate_audio_file(file_path: Path) -> bool:
    """
    Проверяет корректность созданного аудиофайла
    
    Args:
        file_path: Путь к аудиофайлу
        
    Returns:
        bool: True если файл корректен
    """
    try:
        if not file_path.exists():
            return False
        
        # Проверяем размер файла (должен быть больше 0)
        if file_path.stat().st_size == 0:
            return False
        
        # Проверяем, что это действительно аудиофайл (базовая проверка)
        with open(file_path, 'rb') as f:
            header = f.read(4)
            # MP3 файлы обычно начинаются с ID3 тега или синхронизационного слова
            if header.startswith(b'ID3') or header.startswith(b'\xff\xfb'):
                return True
        
        return False
        
    except Exception as e:
        #logger.error(f"Ошибка валидации аудиофайла: {e}")
        return False

def prepare_text_for_tts(text: str) -> str:
    """
    Подготавливает текст для TTS (очистка, форматирование)
    
    Args:
        text: Исходный текст
        
    Returns:
        str: Подготовленный текст
    """
    if not text:
        return ""
    
    # Убираем лишние пробелы и переносы строк
    text = ' '.join(text.split())
    
    # Заменяем некоторые символы для лучшего произношения
    replacements = {
        '&': ' и ',
        '@': ' собака ',
        '#': ' хештег ',
        '%': ' процент ',
        '$': ' доллар ',
        '€': ' евро ',
        '₽': ' рубль ',
        '+': ' плюс ',
        '=': ' равно ',
        '<': ' меньше ',
        '>': ' больше ',
        '|': ' или ',
        '\\': ' слеш ',
        '/': ' слеш ',
        '_': ' подчеркивание ',
        '^': ' степень ',
        '~': ' тильда ',
        '`': '',
        '*': '',
        '[': '',
        ']': '',
        '{': '',
        '}': '',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Убираем множественные пробелы
    text = ' '.join(text.split())
    
    return text.strip()