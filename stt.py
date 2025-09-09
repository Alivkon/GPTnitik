"""
Модуль для преобразования речи в текст с использованием OpenAI Whisper
"""
import asyncio
import logging
from pathlib import Path
from openai import AsyncOpenAI
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from config import OPENAI_API_KEY
from utils import create_temp_file, cleanup_temp_file

#logger = logging.getLogger(__name__)

# Инициализируем клиент OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def convert_to_wav(input_path: Path, max_duration_minutes: int = 7) -> Path:
    """
    Конвертирует аудиофайл в WAV формат 16kHz
    
    Args:
        input_path: Путь к исходному файлу
        max_duration_minutes: Максимальная длительность в минутах
        
    Returns:
        Path: Путь к сконвертированному WAV файлу
        
    Raises:
        ValueError: Если файл слишком длинный или поврежден
    """
    output_path = create_temp_file('.wav')
    
    try:
        # Загружаем аудиофайл
        audio = AudioSegment.from_file(str(input_path))
        
        # Проверяем длительность
        duration_minutes = len(audio) / 1000 / 60  # длительность в минутах
        if duration_minutes > max_duration_minutes:
            raise ValueError(f"Аудио слишком длинное: {duration_minutes:.1f} мин (макс. {max_duration_minutes} мин)")
        
        # Конвертируем в моно, 16kHz
        audio = audio.set_channels(1)  # моно
        audio = audio.set_frame_rate(16000)  # 16kHz
        
        # Экспортируем в WAV
        audio.export(str(output_path), format="wav")
        
        #logger.info(f"Аудио сконвертировано: {duration_minutes:.1f} мин, {output_path}")
        return output_path
        
    except CouldntDecodeError:
        cleanup_temp_file(output_path)
        raise ValueError("Не удалось декодировать аудиофайл. Возможно, файл поврежден.")
    except Exception as e:
        cleanup_temp_file(output_path)
        #logger.error(f"Ошибка конвертации аудио: {e}")
        raise ValueError(f"Ошибка обработки аудио: {str(e)}")

async def speech_to_text(file_path: Path) -> str:
    """
    Преобразует аудиофайл в текст с использованием OpenAI Whisper
    
    Args:
        file_path: Путь к аудиофайлу
        
    Returns:
        str: Распознанный текст
        
    Raises:
        ValueError: При ошибках распознавания или обработки
    """
    wav_path = None
    
    try:
        # Конвертируем в WAV если нужно
        if file_path.suffix.lower() != '.wav':
            wav_path = await convert_to_wav(file_path)
            audio_file_path = wav_path
        else:
            audio_file_path = file_path
        
        # Проверяем размер файла (OpenAI имеет лимит 25MB)
        file_size_mb = audio_file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 25:
            raise ValueError(f"Файл слишком большой: {file_size_mb:.1f}MB (макс. 25MB)")
        
        # Отправляем на распознавание
        with open(audio_file_path, 'rb') as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"  # Указываем русский язык для лучшего качества
            )
        
        text = transcript.text.strip()
        
        if not text:
            raise ValueError("Не удалось распознать речь. Попробуйте говорить громче и четче.")
        
        #logger.info(f"STT успешно: {len(text)} символов")
        return text
        
    except Exception as e:
        #logger.error(f"Ошибка STT: {e}")
        if "rate limit" in str(e).lower():
            raise ValueError("Слишком много запросов. Попробуйте через минуту.")
        elif "invalid" in str(e).lower():
            raise ValueError("Не удалось обработать аудиофайл. Попробуйте записать заново.")
        else:
            raise ValueError("Не расслышал. Попробуй ещё раз.")
    
    finally:
        # Очищаем временный WAV файл
        if wav_path:
            cleanup_temp_file(wav_path)

async def get_audio_duration(file_path: Path) -> float:
    """
    Получает длительность аудиофайла в секундах
    
    Args:
        file_path: Путь к аудиофайлу
        
    Returns:
        float: Длительность в секундах
    """
    try:
        audio = AudioSegment.from_file(str(file_path))
        duration = len(audio) / 1000.0  # длительность в секундах
        print(f"Длительность аудио {file_path}: {duration:.2f} секунд")
    except Exception as e:
        #logger.error(f"Ошибка получения длительности аудио: {e}")
        return 0.0