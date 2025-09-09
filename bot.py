"""
Основной модуль Telegram-бота для сервиса психологической поддержки «Изливание души»
"""
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.error import TelegramError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('session.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Отключаем избыточное логирование HTTP запросов
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('openai._base_client').setLevel(logging.WARNING)

# Импорты наших модулей
from config import TELEGRAM_TOKEN, MAX_MESSAGES_PER_SESSION, SESSION_DURATION_MINUTES
from utils import SessionTimer, send_to_admins, log_session, cleanup_old_temp_files, create_temp_file, cleanup_temp_file
from stt import speech_to_text, get_audio_duration
from gpt import get_gpt_response, validate_user_input
from tts import text_to_speech, prepare_text_for_tts
from admin import cmd_prompt, cmd_setprompt, cmd_resetprompt, cmd_stats, cmd_cleanup

# Состояния FSM
AWAIT_NAME, MAIN_MENU, RECORDING = range(3)

class PsychologyBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.application = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"[START] Пользователь {user_id} ({user.first_name}) начал сессию")
        logger.debug(f"[START] Update: {update}")
        logger.debug(f"[START] Chat ID: {update.effective_chat.id}")
        
        # Инициализируем данные пользователя
        context.user_data.clear()
        context.user_data['user_id'] = user_id
        context.user_data['start_time'] = datetime.now()
        context.user_data['timer'] = SessionTimer()
        context.user_data['message_count'] = 0
        context.user_data['name'] = "Пользователь"
        
        # Очищаем старые временные файлы
        cleanup_old_temp_files()
        
        # Приветственное сообщение
        welcome_text = (
            "Привет! Это пространство, где можно поныть, не боясь осуждения. "
            "Я здесь, чтобы выслушать и поддержать.\n\n"
            "Как к тебе можно обращаться? (имя необязательно)"
        )
        
        # Клавиатура с кнопками
        keyboard = [
            [KeyboardButton("Ввести имя")],
            [KeyboardButton("Пропустить")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        return AWAIT_NAME
    
    async def handle_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик ввода имени"""
        message_text = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"[NAME_INPUT] Пользователь {user_id} ввел: '{message_text}'")
        
        if message_text == "Пропустить":
            logger.info(f"[NAME_INPUT] Пользователь {user_id} пропустил ввод имени")
            context.user_data['name'] = "Пользователь"
            # Убираем клавиатуру перед переходом к главному меню
            try:
                await update.message.reply_text(
                    "Хорошо, будем называть тебя просто Пользователь! 😊",
                    reply_markup=ReplyKeyboardRemove()
                )
                logger.info(f"[NAME_INPUT] Клавиатура убрана для пользователя {user_id}")
            except Exception as e:
                logger.error(f"[NAME_INPUT] Ошибка убирания клавиатуры для пользователя {user_id}: {e}")
            return await self.show_main_menu(update, context)
        elif message_text == "Ввести имя":
            logger.info(f"[NAME_INPUT] Пользователь {user_id} выбрал ввести имя")
            try:
                await update.message.reply_text(
                    "Напиши своё имя:",
                    reply_markup=ReplyKeyboardRemove()
                )
                logger.info(f"[NAME_INPUT] Отправлен запрос имени пользователю {user_id}")
            except Exception as e:
                logger.error(f"[NAME_INPUT] Ошибка отправки сообщения пользователю {user_id}: {e}")
            return AWAIT_NAME
        else:
            # Пользователь ввел имя
            name = message_text.strip()
            if len(name) > 50:
                name = name[:50]
            if len(name) < 1:
                name = "Пользователь"
            
            logger.info(f"[NAME_INPUT] Пользователь {user_id} установил имя: '{name}'")
            context.user_data['name'] = name
            # Убираем клавиатуру (если она была) перед переходом к главному меню
            try:
                await update.message.reply_text(
                    f"Приятно познакомиться, {name}! 😊",
                    reply_markup=ReplyKeyboardRemove()
                )
                logger.info(f"[NAME_INPUT] Клавиатура убрана после ввода имени для пользователя {user_id}")
            except Exception as e:
                logger.error(f"[NAME_INPUT] Ошибка убирания клавиатуры после ввода имени для пользователя {user_id}: {e}")
            return await self.show_main_menu(update, context)
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Переходит сразу к записи голосового сообщения"""
        user_id = update.effective_user.id
        name = context.user_data.get('name', 'Пользователь')
        
        logger.info(f"[MAIN_MENU] Переходим к записи для пользователя {user_id} (имя: {name})")
        
        try:
            await update.message.reply_text(
                "Теперь можешь рассказать мне, что тебя беспокоит 🎙\n\n"
                "🎙 Нажмите на значёк 'микрофон' и говорите... (отпустите, чтобы отправить)\n\n"
                "Максимальная длительность одного сообщения: 7 минут",
                reply_markup=ReplyKeyboardRemove()
            )
            logger.info(f"[MAIN_MENU] Сообщение о записи отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"[MAIN_MENU] Ошибка отправки сообщения пользователю {user_id}: {e}")
        
        return RECORDING
    
    async def start_recording(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начинает запись голосового сообщения"""
        # Проверяем таймер сессии
        timer = context.user_data.get('timer')
        if timer and timer.is_expired():
            return await self.end_session(update, context)
        
        await update.message.reply_text(
            "🎙 Нажмите на значёк 'микрофон' и говорите... (отпустите, чтобы отправить)\n\n"
            "Максимальная длительность одного сообщения: 7 минут",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return RECORDING
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик голосовых сообщений"""
        user_id = update.effective_user.id
        user_name = context.user_data.get('name', 'Пользователь')
        
        logger.info(f"[VOICE] Получено голосовое сообщение от пользователя {user_id} ({user_name})")
        
        # Проверяем таймер сессии
        timer = context.user_data.get('timer')
        if timer and timer.is_expired():
            logger.info(f"[VOICE] Сессия пользователя {user_id} истекла, завершаем")
            return await self.end_session(update, context)
        
        voice_file = None
        wav_file = None
        tts_file = None
        
        try:
            logger.info(f"[VOICE] Начинаем обработку голосового сообщения от {user_id}")
            
            # Показываем индикацию "записывает голосовое сообщение"
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
            
            # Получаем голосовое сообщение
            voice = update.message.voice
            duration_seconds = voice.duration
            
            logger.info(f"[VOICE] Длительность голосового сообщения: {duration_seconds} сек")
            
            # Проверяем длительность
            if duration_seconds > 420:  # 7 минут
                logger.warning(f"[VOICE] Сообщение от {user_id} слишком длинное: {duration_seconds} сек")
                await update.message.reply_text(
                    f"❌ Сообщение слишком длинное ({duration_seconds//60}:{duration_seconds%60:02d}). "
                    "Максимум 7 минут. Попробуйте записать покороче."
                )
                return RECORDING
            
            # Скачиваем файл
            voice_file = create_temp_file('.ogg')
            logger.info(f"[VOICE] Скачиваем голосовой файл в {voice_file}")
            
            file = await context.bot.get_file(voice.file_id)
            await file.download_to_drive(voice_file)
            
            logger.info(f"[VOICE] Файл скачан, размер: {voice_file.stat().st_size} байт")
            
            # Отправляем голосовое сообщение администраторам (если включен DEBUG)
            logger.debug(f"[VOICE] Отправляем голосовое сообщение администраторам")
            await send_to_admins(
                context.bot, 
                "Voice (user)", 
                voice_file=voice_file,
                user_name=user_name
            )
            
            # Показываем индикацию "обрабатывает"
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Преобразуем речь в текст
            logger.info(f"[VOICE] Начинаем STT для пользователя {user_id}")
            try:
                # Проверяем файл
                if not voice_file or not voice_file.exists():
                    raise ValueError("Голосовой файл отсутствует или недоступен")
                
                # Проверяем размер файла
                file_size = voice_file.stat().st_size
                if file_size == 0:
                    raise ValueError("Голосовой файл пуст")
                
                # Пытаемся выполнить STT
                try:
                    user_text = await speech_to_text(voice_file)
                except ConnectionError:
                    raise ValueError("Сервис распознавания речи недоступен. Попробуйте позже.")
                except Exception as stt_error:
                    logger.error(f"[VOICE] Ошибка сервиса STT: {stt_error}")
                    raise ValueError("Ошибка при распознавании речи. Попробуйте ещё раз.")
                
                # Проверяем результат
                if not user_text or len(user_text.strip()) == 0:
                    raise ValueError("Не удалось распознать речь. Пожалуйста, говорите чётче.")
                
                logger.info(f"[VOICE] STT успешно: '{user_text[:100]}...' (длина: {len(user_text)})")
                
            except ValueError as e:
                error_msg = str(e)
                logger.error(f"[VOICE] Ошибка STT для пользователя {user_id}: {error_msg}")
                
                # Отправляем понятное пользователю сообщение об ошибке
                user_msg = f"❌ {error_msg}"
                try:
                    await update.message.reply_text(user_msg)
                except Exception as send_error:
                    logger.error(f"[VOICE] Не удалось отправить сообщение об ошибке: {send_error}")
                
                return RECORDING
            
            # Проверяем корректность распознанного текста
            if not validate_user_input(user_text):
                logger.warning(f"[VOICE] Некорректный текст от пользователя {user_id}: '{user_text}'")
                await update.message.reply_text(
                    "❌ Не удалось разобрать речь. Попробуйте говорить четче и громче."
                )
                return RECORDING
            
            # Отправляем STT результат администраторам
            logger.debug(f"[VOICE] Отправляем STT результат администраторам")
            await send_to_admins(
                context.bot, 
                "STT", 
                content=user_text,
                user_name=user_name
            )
            
            # Показываем индикацию "генерирует ответ"
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Получаем ответ от GPT
            logger.info(f"[VOICE] Отправляем запрос к GPT для пользователя {user_id}")
            try:
                gpt_response = await get_gpt_response(user_text, user_name)
                logger.info(f"[VOICE] GPT отв��т получен: '{gpt_response[:100]}...' (длина: {len(gpt_response)})")
            except ValueError as e:
                logger.error(f"[VOICE] Ошибка GPT для пользователя {user_id}: {e}")
                await update.message.reply_text(f"❌ {str(e)}")
                return RECORDING
            
            # Отправляем GPT ответ администраторам
            logger.debug(f"[VOICE] Отправляем GPT ответ администраторам")
            await send_to_admins(
                context.bot, 
                "GPT", 
                content=gpt_response,
                user_name=user_name
            )
            
            # Показываем индикацию "озвучивает"
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
            
            # Преобразуем ответ в речь
            logger.info(f"[VOICE] Начинаем TTS для пользователя {user_id}")
            try:
                prepared_text = prepare_text_for_tts(gpt_response)
                tts_file = await text_to_speech(prepared_text)
                logger.info(f"[VOICE] TTS успешно создан: {tts_file}")
            except ValueError as e:
                logger.error(f"[VOICE] Ошибка TTS для пользователя {user_id}: {e}")
                # Если TTS не работает, отправляем текстом
                await update.message.reply_text(f"💬 {gpt_response}")
                await update.message.reply_text(f"❌ Ошибка озвучивания: {str(e)}")
                return await self.continue_or_end(update, context)
            
            # Отправляем голосовой ответ пользователю
            logger.info(f"[VOICE] Отправляем голосовой ответ пользователю {user_id}")
            try:
                with open(tts_file, 'rb') as audio:
                    await context.bot.send_voice(
                        chat_id=update.effective_chat.id,
                        voice=audio
                    )
                logger.info(f"[VOICE] Голосовой ответ успешно отправлен пользователю {user_id}")
            except Exception as e:
                logger.error(f"[VOICE] Ошибка отправки голосового ответа пользователю {user_id}: {e}")
                # Отправляем текстом как fallback
                await update.message.reply_text(f"💬 {gpt_response}")
            
            # Отправляем голосовой ответ администраторам (��сли включен DEBUG)
            logger.debug(f"[VOICE] Отправляем голосовой ответ администраторам")
            await send_to_admins(
                context.bot, 
                "Voice (bot)", 
                voice_file=tts_file,
                user_name=user_name
            )
            
            # Увеличиваем счетчик сообщений
            context.user_data['message_count'] = context.user_data.get('message_count', 0) + 1
            logger.info(f"[VOICE] Обработка завершена для пользователя {user_id}, сообщений: {context.user_data['message_count']}")
            
            return await self.continue_or_end(update, context)
            
        except Exception as e:
            logger.error(f"[VOICE] Критическая ошибка обработки голосового сообщения от {user_id}: {e}")
            logger.exception("Полная трассировка ошибки:")
            try:
                await update.message.reply_text(
                    "❌ Извини, произошла ошибка. Попробуй ещё раз."
                )
            except Exception as send_error:
                logger.error(f"[VOICE] Не удалось отправить сообщение об ошибке пользователю {user_id}: {send_error}")
            return RECORDING
            
        finally:
            # Очищаем временные файлы
            logger.debug(f"[VOICE] Очищаем временные файлы для пользователя {user_id}")
            for temp_file in [voice_file, wav_file, tts_file]:
                if temp_file:
                    cleanup_temp_file(temp_file)
    
    async def continue_or_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Предлагает продолжить или завершить сессию"""
        timer = context.user_data.get('timer')
        message_count = context.user_data.get('message_count', 0)
        
        # Проверяем лимит времени
        if timer and timer.is_expired():
            return await self.end_session(update, context)
        
        # Проверяем лимит сообщений
        if message_count >= MAX_MESSAGES_PER_SESSION:
            await update.message.reply_text(
                f"Достигнут лимит сообщений ({MAX_MESSAGES_PER_SESSION}) для одной сессии. "
                "Сессия будет завершена."
            )
            return await self.end_session(update, context)
        
        await update.message.reply_text(
            "Хочешь ещё что-то рассказать?\n\n"
            "🎙 Нажмите на значёк 'микрофон' и говорите... (отпустите, чтобы отправить)\n\n"
            f"Максимальная длительность одного сообщения: 7 минут\n"
            f"а продолжительность всего разговора не более {SESSION_DURATION_MINUTES} минут",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return RECORDING
    
    async def end_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Завершает сессию"""
        timer = context.user_data.get('timer')
        user_name = context.user_data.get('name', 'Пользователь')
        message_count = context.user_data.get('message_count', 0)
        
        # Логируем сессию
        if timer:
            duration = timer.elapsed_time()
            log_session(user_name, duration, message_count)
        
        # Прощальное сообщение
        await update.message.reply_text(
            "Сессия завершена. Спасибо, что доверил мне свои мысли. 💙\n\n"
            "Помни: ты не один, и твои чувства важны.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Кнопка для новой сессии
        keyboard = [[KeyboardButton("Начать снова")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            "Если захочешь поговорить ещё — я здесь.",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
    
    async def handle_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик кнопки 'Начать снова'"""
        return await self.start_command(update, context)
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик текстовых сообщений"""
        message_text = update.message.text
        user_id = update.effective_user.id
        current_state = context.user_data.get('current_state', 'UNKNOWN')
        
        logger.info(f"[TEXT] Пользователь {user_id} отправил текст: '{message_text}' (состояние: {current_state})")
        
        if message_text == "Начать снова":
            logger.info(f"[TEXT] Пользователь {user_id} нажал кнопку 'Начать снова'")
            return await self.handle_restart(update, context)
        else:
            logger.info(f"[TEXT] Пользователь {user_id} отправил неизвестное сообщение: '{message_text}'")
            try:
                await update.message.reply_text(
                    "Я понимаю только голосовые сообщения. Нажмите на значёк 'микрофон' и говорите."
                )
                logger.info(f"[TEXT] Отправлено напоминание пользователю {user_id}")
            except Exception as e:
                logger.error(f"[TEXT] Ошибка отправки напоминания пользователю {user_id}: {e}")
            return MAIN_MENU
    
    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /cancel"""
        await update.message.reply_text(
            "Сессия отменена. До свидания! 👋",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок"""
        logger.error(f"Ошибка бота: {context.error}")
        
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте ещё раз или начните сначала с /start"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
    
    def setup_handlers(self):
        """Настраивает обработчики сообщений"""
        # Основной conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start_command),
                MessageHandler(filters.Regex('^Начать снова$'), self.handle_restart)
            ],
            states={
                AWAIT_NAME: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, 
                        self.handle_name_input
                    )
                ],
                MAIN_MENU: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, 
                        self.handle_text_message
                    )
                ],
                RECORDING: [
                    MessageHandler(
                        filters.VOICE, 
                        self.handle_voice_message
                    ),
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, 
                        self.handle_text_message
                    )
                ]
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel_command),
                CommandHandler('start', self.start_command)
            ]
        )
        
        # Добавляем conversation handler
        self.application.add_handler(conv_handler)
        
        # Административные команды
        self.application.add_handler(CommandHandler('prompt', cmd_prompt))
        self.application.add_handler(CommandHandler('setprompt', cmd_setprompt))
        self.application.add_handler(CommandHandler('resetprompt', cmd_resetprompt))
        self.application.add_handler(CommandHandler('stats', cmd_stats))
        self.application.add_handler(CommandHandler('cleanup', cmd_cleanup))
        
        # Обработчик ошибок
        self.application.add_error_handler(self.error_handler)
    
    async def run(self):
        """Запускает бота"""
        # Создаем приложение
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Настраиваем обработчики
        self.setup_handlers()
        
        logger.info("Бот запущен и готов к работе!")
        
        # Инициализируем приложение
        await self.application.initialize()
        
        try:
            # Запускаем бота
            await self.application.start()
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
            # Ждем бесконечно
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        finally:
            # Корректно останавливаем бота
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

async def main():
    """Главная функция"""
    bot = PsychologyBot()
    await bot.run()

if __name__ == '__main__':
    try:
        # Проверяем, есть ли уже запущенный event loop
        try:
            loop = asyncio.get_running_loop()
            # Если loop уже запущен, используем create_task
            task = loop.create_task(main())
            # Ждем завершения в отдельном потоке
            import threading
            import concurrent.futures
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(main())
                finally:
                    new_loop.close()
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
        except RuntimeError:
            # Если loop не запущен, запускаем обычным способом
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise