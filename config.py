"""
Конфигурация бота и утилиты для работы с настройками
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
#logging.basicConfig(
#    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#    level=logging.DEBUG,  # Изменили на DEBUG для более подробных логов
#    handlers=[
#        logging.FileHandler('session.log', encoding='utf-8'),
#        logging.StreamHandler()
#    ]
#)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ADMIN_IDS = [
    int(os.getenv('ADMIN_ID_1', 0)),
    int(os.getenv('ADMIN_ID_2', 0))
]
DEBUG_SEND_VOICE = os.getenv('DEBUG_SEND_VOICE', 'false').lower() == 'true'

# Лимиты пользователей
MAX_MESSAGES_PER_SESSION = int(os.getenv('MAX_MESSAGES_PER_SESSION', 10))
SESSION_DURATION_MINUTES = int(os.getenv('SESSION_DURATION_MINUTES', 30))

# Пути
DATA_DIR = Path('data')
TEMP_DIR = Path('temp')
PROMPT_FILE = DATA_DIR / 'prompt.txt'

# Создаем необходимые директории
DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Стандартный промпт
DEFAULT_PROMPT = """Ты — поддерживающий и доброжелательный собеседник. Пользователь хочет выговориться. Отвечай тёплым, спокойным тоном, с эмпатией. Не давай советов, если не просят. Отвечай коротко — 2–4 предложения."""

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

def read_prompt() -> str:
    """Читает системный промпт из файла"""
    try:
        if PROMPT_FILE.exists():
            return PROMPT_FILE.read_text(encoding='utf-8').strip()
        else:
            # Создаем файл с промптом по умолчанию
            write_prompt(DEFAULT_PROMPT)
            return DEFAULT_PROMPT
    except Exception as e:
        logger.error(f"Ошибка чтения промпта: {e}")
        return DEFAULT_PROMPT

def write_prompt(prompt: str) -> bool:
    """Записывает системный промпт в файл"""
    try:
        PROMPT_FILE.write_text(prompt, encoding='utf-8')
        logger.info(f"Промпт обновлён: {prompt[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Ошибка записи промпта: {e}")
        return False

def reset_prompt() -> bool:
    """Сбрасывает промпт к значению по умолчанию"""
    return write_prompt(DEFAULT_PROMPT)

# Проверяем наличие обязательных переменных
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден в .env файле")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в .env файле")
if not any(ADMIN_IDS):
    pass  # logger.warning("Администраторы не настроены в .env файле")