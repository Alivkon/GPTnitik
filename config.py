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
   # int(os.getenv('ADMIN_ID_2', 0))
]
DEBUG_SEND_VOICE = os.getenv('DEBUG_SEND_VOICE', 'false').lower() == 'true'

# Лимиты пользователей (глобальные переменные для динамического изменения)
MAX_MESSAGES_PER_SESSION = int(os.getenv('MAX_MESSAGES_PER_SESSION', 10))
SESSION_DURATION_MINUTES = int(os.getenv('SESSION_DURATION_MINUTES', 30))

# Пути
DATA_DIR = Path('data')
TEMP_DIR = Path('temp')
PROMPT_FILE = DATA_DIR / 'prompt.txt'
LIMITS_FILE = DATA_DIR / 'limits.txt'

# Создаем необходимые директории
DATA_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Настройки GPT
MAX_TOKENS = int(os.getenv('MAX_TOKENS', 500))

# Файл для хранения настроек токенов
TOKENS_FILE = DATA_DIR / 'tokens.txt'

def get_current_max_tokens() -> int:
    """
    Получает текущий лимит токенов
    
    Returns:
        Текущий лимит токенов
    """
    try:
        if TOKENS_FILE.exists():
            with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return int(content)
    except (ValueError, FileNotFoundError):
        pass
    
    # Возвращаем значение по умолчанию
    return int(os.getenv('MAX_TOKENS', 500))

def write_max_tokens(max_tokens: int) -> bool:
    """
    Записывает новый лимит токенов в файл
    
    Args:
        max_tokens: Новый лимит токенов
        
    Returns:
        True если успешно запи��ано, False в случае ошибки
    """
    try:
        # Создаем директорию если не существует
        DATA_DIR.mkdir(exist_ok=True)
        
        with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
            f.write(str(max_tokens))
        
        # Обновляем глобальную переменную
        global MAX_TOKENS
        MAX_TOKENS = max_tokens
        
        return True
    except Exception as e:
        logger.error(f"Ошибка записи лимита токенов: {e}")
        return False

def reset_max_tokens() -> bool:
    """
    Сбрасывает лимит токенов к значению по умолчанию
    
    Returns:
        True если успешно сброшено, False в случае ошибки
    """
    try:
        default_tokens = int(os.getenv('MAX_TOKENS', 500))
        
        if TOKENS_FILE.exists():
            TOKENS_FILE.unlink()
        
        # Обновляем глобальную переменную
        global MAX_TOKENS
        MAX_TOKENS = default_tokens
        
        return True
    except Exception as e:
        logger.error(f"Ошибка сброса лимита токенов: {e}")
        return False

# Загружаем актуальное значение при импорте модуля
MAX_TOKENS = get_current_max_tokens()

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

def read_limits() -> tuple[int, int]:
    """Читает лимиты из файла или возвращает текущие значения"""
    try:
        if LIMITS_FILE.exists():
            content = LIMITS_FILE.read_text(encoding='utf-8').strip()
            lines = content.split('\n')
            if len(lines) >= 2:
                max_messages = int(lines[0].split('=')[1])
                session_duration = int(lines[1].split('=')[1])
                return max_messages, session_duration
    except Exception as e:
        logger.error(f"Ошибка чтения лимитов: {e}")
    
    # Возвращаем текущие значения если файл не существует или есть ошибка
    return MAX_MESSAGES_PER_SESSION, SESSION_DURATION_MINUTES

def write_limits(max_messages: int, session_duration: int) -> bool:
    """Записывает лимиты в файл и обновляет глобальные переменные"""
    global MAX_MESSAGES_PER_SESSION, SESSION_DURATION_MINUTES
    
    try:
        content = f"MAX_MESSAGES_PER_SESSION={max_messages}\nSESSION_DURATION_MINUTES={session_duration}\n"
        LIMITS_FILE.write_text(content, encoding='utf-8')
        
        # Обновляем глобальные переменные
        MAX_MESSAGES_PER_SESSION = max_messages
        SESSION_DURATION_MINUTES = session_duration
        
        logger.info(f"Лимиты обновлены: {max_messages} сообщений, {session_duration} минут")
        return True
    except Exception as e:
        logger.error(f"Ошибка записи лимитов: {e}")
        return False

def get_current_limits() -> tuple[int, int]:
    """Возвращает текущие лимиты"""
    return MAX_MESSAGES_PER_SESSION, SESSION_DURATION_MINUTES

def reset_limits() -> bool:
    """Сбрасывает лимиты к значениям по умолчанию из .env"""
    default_messages = int(os.getenv('MAX_MESSAGES_PER_SESSION', 10))
    default_duration = int(os.getenv('SESSION_DURATION_MINUTES', 30))
    return write_limits(default_messages, default_duration)

# Загружаем лимиты из файла при запуске (если файл существует)
def _load_limits_on_startup():
    """Загружает лимиты из файла при запуске модуля"""
    global MAX_MESSAGES_PER_SESSION, SESSION_DURATION_MINUTES
    try:
        if LIMITS_FILE.exists():
            max_messages, session_duration = read_limits()
            MAX_MESSAGES_PER_SESSION = max_messages
            SESSION_DURATION_MINUTES = session_duration
            logger.info(f"Лимиты загружены из файла: {max_messages} сообщений, {session_duration} минут")
    except Exception as e:
        logger.error(f"Ошибка загрузки лимитов при запуске: {e}")

# Загружаем лимиты при ��мпорте модуля
_load_limits_on_startup()

# Проверяем наличие обязательных переменных
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден в .env файле")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в .env файле")
if not any(ADMIN_IDS):
    pass  # logger.warning("Администраторы не настроены в .env файле")