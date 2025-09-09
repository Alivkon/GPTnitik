"""
Утилиты для работы с временными файлами, таймерами и отправкой сообщений администраторам
"""
import os
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from telegram import Bot
from telegram.error import TelegramError
import logging

from config import ADMIN_IDS, TEMP_DIR, DEBUG_SEND_VOICE, SESSION_DURATION_MINUTES

logger = logging.getLogger(__name__)

class SessionTimer:
    """Класс для отслеживания времени сессии"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.max_duration = timedelta(minutes=SESSION_DURATION_MINUTES)
    
    def is_expired(self) -> bool:
        """Проверяет, истекло ли время сессии"""
        return datetime.now() - self.start_time > self.max_duration
    
    def remaining_time(self) -> timedelta:
        """Возвращает оставшееся время сессии"""
        elapsed = datetime.now() - self.start_time
        remaining = self.max_duration - elapsed
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def elapsed_time(self) -> timedelta:
        """Возвращает прошедшее время"""
        return datetime.now() - self.start_time

def create_temp_file(suffix: str = '.tmp') -> Path:
    """Создает временный файл и возвращает путь к нему"""
    timestamp = int(time.time() * 1000000)  # микросекунды для уникальности
    filename = f"temp_{timestamp}{suffix}"
    return TEMP_DIR / filename

def cleanup_temp_file(file_path: Path) -> None:
    """Удаляет временный файл"""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Удален временный файл: {file_path}")
    except Exception as e:
        logger.error(f"Ошибка удаления временного файла {file_path}: {e}")

def cleanup_old_temp_files(max_age_hours: int = 1) -> None:
    """Удаляет старые временные файлы"""
    try:
        cutoff_time = time.time() - (max_age_hours * 3600)
        for file_path in TEMP_DIR.glob('temp_*'):
            if file_path.stat().st_mtime < cutoff_time:
                print("Здесь удаление временного аудиофайла ")
                #cleanup_temp_file(file_path)
    except Exception as e:
        logger.error(f"Ошибка очистки временных файлов: {e}")

async def send_to_admins(
    bot: Bot, 
    message_type: str, 
    content: str = None, 
    voice_file: Path = None,
    user_name: str = "Пользователь"
) -> None:
    """
    Отправляет сообщение администраторам
    
    Args:
        bot: Экземпляр бота
        message_type: Тип сообщения (STT, GPT, Voice (user), Voice (bot))
        content: Текстовое содержимое
        voice_file: Путь к голосовому файлу (если нужно отправить)
        user_name: Имя пользователя
    """
    if not ADMIN_IDS:
        return
    
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # Формируем заголовок сообщения
    header = f"[Пользователь: {user_name}]\n[Время: {current_time}]\n[Тип: {message_type}]"
    
    for admin_id in ADMIN_IDS:
        if admin_id == 0:  # Пропускаем некорректные ID
            continue
            
        try:
            if voice_file and voice_file.exists():
                # Отправляем голосовое сообщение
                if DEBUG_SEND_VOICE or message_type in ['Voice (user)', 'Voice (bot)']:
                    with open(voice_file, 'rb') as audio:
                        await bot.send_voice(
                            chat_id=admin_id,
                            voice=audio,
                            caption=header
                        )
            elif content:
                # Отправляем текстовое сообщение
                full_message = f"{header}\n[Содержание: {content}]"
                await bot.send_message(
                    chat_id=admin_id,
                    text=full_message
                )
                
        except TelegramError as e:
            logger.error(f"Ошибка отправки сообщения админу {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке админу {admin_id}: {e}")

def log_session(user_name: str, duration: timedelta, message_count: int, error: str = None) -> None:
    """Логирует информацию о сессии"""
    try:
        duration_str = f"{int(duration.total_seconds() // 60)} мин"
        log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {user_name} | Сессия: {duration_str} | Обменов: {message_count}"
        
        if error:
            log_entry += f" | Ошибка: {error}"
            
        logger.info(log_entry)
        
    except Exception as e:
        logger.error(f"Ошибка логирования сессии: {e}")

def format_duration(duration: timedelta) -> str:
    """Форматирует продолжительность в читаемый вид"""
    total_seconds = int(duration.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    if minutes > 0:
        return f"{minutes}:{seconds:02d}"
    else:
        return f"0:{seconds:02d}"