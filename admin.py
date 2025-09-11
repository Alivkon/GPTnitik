"""
Модуль для административных команд
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import is_admin, read_prompt, write_prompt, reset_prompt

logger = logging.getLogger(__name__)

async def cmd_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /prompt - показывает текущий системный промпт
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        current_prompt = read_prompt()
        
        message = f"📝 **Текущий системный промпт:**\n\n```\n{current_prompt}\n```"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Админ {user_id} запросил текущий промпт")
        
    except Exception as e:
        logger.error(f"Ошибка команды /prompt: {e}")
        await update.message.reply_text("❌ Ошибка при получении промпта.")

async def cmd_setprompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /setprompt - устанавливает новый системный промпт
    Использование: /setprompt Новый текст промпта...
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    # Получаем новый промпт из аргументов команды
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите новый промпт.\n"
            "Использование: `/setprompt Новый текст промпта...`",
            parse_mode='Markdown'
        )
        return
    
    new_prompt = ' '.join(context.args)
    
    if len(new_prompt.strip()) < 10:
        await update.message.reply_text("❌ Промпт слишком короткий (минимум 10 символов).")
        return
    
    if len(new_prompt) > 2000:
        await update.message.reply_text("❌ Промпт слишком длинный (максимум 2000 символов).")
        return
    
    try:
        success = write_prompt(new_prompt)
        
        if success:
            await update.message.reply_text("✅ Промпт обновлён.")
            logger.info(f"Админ {user_id} обновил промпт: {new_prompt[:50]}...")
        else:
            await update.message.reply_text("❌ Ошибка при сохранении промпта.")
            
    except Exception as e:
        logger.error(f"Ошибка команды /setprompt: {e}")
        await update.message.reply_text("❌ Ошибка при обновлении промпта.")

async def cmd_resetprompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /resetprompt - сбрасывает промпт к значению по умолчанию
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        success = reset_prompt()
        
        if success:
            await update.message.reply_text("✅ Промпт сброшен к значению по умолчанию.")
            logger.info(f"Админ {user_id} сбросил промпт к значению по умолчанию")
        else:
            await update.message.reply_text("❌ Ошибка при сбросе промпта.")
            
    except Exception as e:
        logger.error(f"Ошибка команды /resetprompt: {e}")
        await update.message.reply_text("❌ Ошибка при сбросе промпта.")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /stats - показывает статистику бота
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        from config import DEBUG_SEND_VOICE, ADMIN_IDS, MAX_MESSAGES_PER_SESSION, SESSION_DURATION_MINUTES
        from utils import TEMP_DIR
        import os
        
        # Подсчитываем временные файлы
        temp_files_count = len(list(TEMP_DIR.glob('*'))) if TEMP_DIR.exists() else 0
        
        # Размер директории с временными файлами
        temp_dir_size = 0
        if TEMP_DIR.exists():
            for file_path in TEMP_DIR.rglob('*'):
                if file_path.is_file():
                    temp_dir_size += file_path.stat().st_size
        
        temp_dir_size_mb = temp_dir_size / (1024 * 1024)
        
        # Получаем информацию о заблокированных пользователях
        try:
            from user_limits import user_limit_manager
            blocked_count = user_limit_manager.get_blocked_users_count()
        except Exception:
            blocked_count = 0
        
        # Получаем информацию о токенах
        try:
            from config import get_current_max_tokens
            current_tokens = get_current_max_tokens()
        except Exception:
            current_tokens = "Неизвестно"
        
        stats_message = f"""📊 **Статистика бота:**

🔧 **Настройки:**
• DEBUG_SEND_VOICE: {DEBUG_SEND_VOICE}
• Администраторов: {len([aid for aid in ADMIN_IDS if aid != 0])}

⏱️ **Лимиты сессий:**
• Максимум сообщений: {MAX_MESSAGES_PER_SESSION}
• Длительность сессии: {SESSION_DURATION_MINUTES} минут

🎯 **Настройки GPT:**
• Лимит токенов: {current_tokens}

🚫 **Заблокированные пользователи:**
• Количество: {blocked_count}

📁 **Временные файлы:**
• Количество: {temp_files_count}
• Размер: {temp_dir_size_mb:.2f} MB

📝 **Промпт:**
• Длина: {len(read_prompt())} символов
"""
        
        await update.message.reply_text(
            stats_message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Админ {user_id} запросил статистику")
        
    except Exception as e:
        logger.error(f"Ошибка команды /stats: {e}")
        await update.message.reply_text("❌ Ошибка при получении статистики.")

async def cmd_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /cleanup - очищает старые временные файлы
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        from utils import cleanup_old_temp_files
        
        # Очищаем файлы старше 1 часа
        cleanup_old_temp_files(max_age_hours=1)
        
        await update.message.reply_text("✅ Временные файлы очищены.")
        logger.info(f"Админ {user_id} запустил очистку временных файлов")
        
    except Exception as e:
        logger.error(f"Ошибка команды /cleanup: {e}")
        await update.message.reply_text("❌ Ошибка при очистке файлов.")

async def cmd_blocked_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /blocked - показывает список заблокированных пользователей
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        from user_limits import user_limit_manager
        
        blocked_users = user_limit_manager.get_blocked_users_info()
        
        if not blocked_users:
            await update.message.reply_text("✅ Заблокированных пользователей нет.")
            return
        
        message = f"🚫 **Заблокированные пользователи ({len(blocked_users)}):**\n\n"
        
        for user_info in blocked_users[-10:]:  # Показываем последние 10
            user_display = f"ID: {user_info['user_id']}"
            if user_info['first_name']:
                user_display += f" ({user_info['first_name']}"
                if user_info['username']:
                    user_display += f" @{user_info['username']}"
                user_display += ")"
            elif user_info['username']:
                user_display += f" (@{user_info['username']})"
            
            blocked_date = user_info['blocked_at'].strftime("%d.%m.%Y %H:%M")
            
            message += f"• {user_display}\n"
            message += f"  📅 {blocked_date}\n"
            message += f"  📝 {user_info['reason']}\n"
            message += f"  💬 {user_info['message_count']} сообщений, {user_info['session_duration']} мин\n\n"
        
        if len(blocked_users) > 10:
            message += f"... и ещё {len(blocked_users) - 10} пользователей"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Админ {user_id} запросил список заблокированных пользователей")
        
    except Exception as e:
        logger.error(f"Ошибка команды /blocked: {e}")
        await update.message.reply_text("❌ Ошибка при получении списка заблокированных пользователей.")

async def cmd_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /unblock - разблокирует пользователя
    Использование: /unblock USER_ID
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите ID пользователя для разблокировки.\n"
            "Использование: `/unblock USER_ID`",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Некорректный ID пользователя.")
        return
    
    try:
        from user_limits import user_limit_manager
        
        if not user_limit_manager.is_user_blocked(target_user_id):
            await update.message.reply_text(f"❌ Пользователь {target_user_id} не заблокирован.")
            return
        
        success = user_limit_manager.unblock_user(target_user_id)
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {target_user_id} разблокирован.")
            logger.info(f"Админ {user_id} разблокировал пользователя {target_user_id}")
        else:
            await update.message.reply_text(f"❌ Ошибка при разблокировке пользователя {target_user_id}.")
        
    except Exception as e:
        logger.error(f"��шибка команды /unblock: {e}")
        await update.message.reply_text("❌ Ошибка при разблокировке пользователя.")

async def cmd_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /block - блокирует пользователя
    Использование: /block USER_ID [причина]
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите ID пользователя для блокировки.\n"
            "Использование: `/block USER_ID [причина]`",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Некорректный ID пользователя.")
        return
    
    # Получаем причину блокировки
    reason = "Заблокирован администратором"
    if len(context.args) > 1:
        reason = ' '.join(context.args[1:])
    
    try:
        from user_limits import user_limit_manager
        
        if user_limit_manager.is_user_blocked(target_user_id):
            await update.message.reply_text(f"❌ Пользователь {target_user_id} уже заблокирован.")
            return
        
        success = user_limit_manager.block_user(
            user_id=target_user_id,
            reason=reason
        )
        
        if success:
            await update.message.reply_text(f"✅ Пользователь {target_user_id} заблокирован.\nПричина: {reason}")
            logger.info(f"Админ {user_id} заблокировал пользователя {target_user_id}. Причина: {reason}")
        else:
            await update.message.reply_text(f"❌ Ошибка при блокировке пользователя {target_user_id}.")
        
    except Exception as e:
        logger.error(f"Ошибка команды /block: {e}")
        await update.message.reply_text("❌ Ошибка при блокировке пользователя.")

async def cmd_cleanup_blocks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /cleanup_blocks - удаляет старые блокировки
    Использование: /cleanup_blocks [дни] (по умолчанию 30 дней)
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    # Получаем количество дней
    days_old = 30
    if context.args:
        try:
            days_old = int(context.args[0])
            if days_old < 1:
                await update.message.reply_text("❌ Количество дней должно быть больше 0.")
                return
        except ValueError:
            await update.message.reply_text("❌ Некорректное количество дней.")
            return
    
    try:
        from user_limits import user_limit_manager
        
        removed_count = user_limit_manager.cleanup_old_blocks(days_old)
        
        await update.message.reply_text(
            f"✅ Удалено {removed_count} старых блокировок (старше {days_old} дней)."
        )
        logger.info(f"Админ {user_id} очистил {removed_count} старых блокировок")
        
    except Exception as e:
        logger.error(f"Ошибка команды /cleanup_blocks: {e}")
        await update.message.reply_text("❌ Ошибка при очистке старых блокировок.")

async def cmd_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /limits - показывает текущие лимиты
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой к��манды.")
        return
    
    try:
        from config import get_current_limits
        
        max_messages, session_duration = get_current_limits()
        
        message = f"""⚙️ **Текущие лимиты пользователей:**

💬 **Максимум сообщений за сессию:** {max_messages}
⏱️ **Максимальная длительность сессии:** {session_duration} минут

Для изменения используйте:
• `/setlimits СООБЩЕНИЯ МИНУТЫ`
• `/resetlimits` - сброс к значениям по умолчанию"""
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Админ {user_id} запросил текущие лимиты")
        
    except Exception as e:
        logger.error(f"Ошибка команды /limits: {e}")
        await update.message.reply_text("❌ Ошибка при получении лимитов.")

async def cmd_setlimits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /setlimits - устанавливает новые лимиты
    Использование: /setlimits СООБЩЕНИЯ МИНУТЫ
    Доступна только ��дминистраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n"
            "Использование: `/setlimits СООБЩЕНИЯ МИНУТЫ`\n\n"
            "Пример: `/setlimits 5 20`",
            parse_mode='Markdown'
        )
        return
    
    try:
        max_messages = int(context.args[0])
        session_duration = int(context.args[1])
        
        # Валидация значений
        if max_messages < 1 or max_messages > 100:
            await update.message.reply_text("❌ Количество сообщений должно быть от 1 до 100.")
            return
        
        if session_duration < 1 or session_duration > 1440:  # максимум 24 часа
            await update.message.reply_text("❌ Длительность сессии должна быть от 1 до 1440 минут (24 часа).")
            return
        
    except ValueError:
        await update.message.reply_text("❌ Некорректны�� значения. Используйте только числа.")
        return
    
    try:
        from config import write_limits
        
        success = write_limits(max_messages, session_duration)
        
        if success:
            await update.message.reply_text(
                f"✅ Лимиты обновлены:\n"
                f"💬 Максимум сообщений: {max_messages}\n"
                f"⏱️ Длительность сессии: {session_duration} минут"
            )
            logger.info(f"Админ {user_id} обновил лимиты: {max_messages} сообщений, {session_duration} минут")
        else:
            await update.message.reply_text("❌ Ошибка при сохранении лимитов.")
            
    except Exception as e:
        logger.error(f"Ошибка команды /setlimits: {e}")
        await update.message.reply_text("❌ Ошибка при обновлении лимитов.")

async def cmd_resetlimits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /resetlimits - сбрасывает лимиты к значениям по умолчанию
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        from config import reset_limits, get_current_limits
        
        success = reset_limits()
        
        if success:
            max_messages, session_duration = get_current_limits()
            await update.message.reply_text(
                f"✅ Лимиты сброшены к значениям по умолчанию:\n"
                f"💬 Максимум сообщений: {max_messages}\n"
                f"⏱️ Длительность сессии: {session_duration} минут"
            )
            logger.info(f"Админ {user_id} сбросил лимиты к значениям по умолчанию")
        else:
            await update.message.reply_text("❌ Ошибка при сбросе лимитов.")
            
    except Exception as e:
        logger.error(f"Ошибка команды /resetlimits: {e}")
        await update.message.reply_text("❌ Ошибка при сбросе лимитов.")

async def cmd_clear_all_blocks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /clearblocks - полностью очищает все блокировки (имитация сброса в 00:00)
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        from user_limits import user_limit_manager
        from datetime import datetime
        
        # Получаем количество заблокированных пользователей до очистки
        blocked_count_before = user_limit_manager.get_blocked_users_count()
        
        if blocked_count_before == 0:
            await update.message.reply_text(
                "ℹ️ **Нет заблокированных пользователей**\n\n"
                "Список уже пуст."
            )
            return
        
        # Выполняем полную очистку
        cleared_count = user_limit_manager.clear_all_blocks()
        
        await update.message.reply_text(
            f"🕛 **Выполнена полная очистка блокировок**\n\n"
            f"✅ Разблокировано пользователей: **{cleared_count}**\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Все пользователи снова могут пользоваться ботом."
        )
        
        logger.info(f"Администратор {user_id} выполнил полную очистку блокировок: {cleared_count} пользователей")
        
    except Exception as e:
        logger.error(f"Ошибка полной очистки блокировок администратором {user_id}: {e}")
        await update.message.reply_text(f"❌ Ошибка очистки блокировок: {str(e)}")

async def cmd_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /tokens - показывает текущий лимит токенов
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        from config import get_current_max_tokens
        import os
        
        current_tokens = get_current_max_tokens()
        default_tokens = int(os.getenv('MAX_TOKENS', 500))
        
        message = f"""🔧 **Настройки токенов GPT:**

🎯 **Текущий лимит:** {current_tokens} токенов
📋 **По умолчанию:** {default_tokens} токенов

ℹ️ **Информация:**
• Токены определяют максимальную длину ответа GPT
• Больше токенов = более длинные ответы
• Меньше токенов = более короткие ответы

**Команды управления:**
• `/settokens КОЛИЧЕСТВО` - установить новый лимит
• `/resettokens` - сброс к значению по умолчанию"""
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
        logger.info(f"Админ {user_id} запросил информацию о токенах")
        
    except Exception as e:
        logger.error(f"Ошибка команды /tokens: {e}")
        await update.message.reply_text("❌ Ошибка при получении информации о токенах.")

async def cmd_settokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /settokens - устанавливает новый лимит токенов
    Использование: /settokens КОЛИЧЕСТВО
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите количество токенов.\n"
            "Использование: `/settokens КОЛИЧЕСТВО`\n\n"
            "Пример: `/settokens 800`",
            parse_mode='Markdown'
        )
        return
    
    try:
        max_tokens = int(context.args[0])
        
        # Валидация значений
        if max_tokens < 50:
            await update.message.reply_text("❌ Минимальное количество токенов: 50")
            return
        
        if max_tokens > 4000:
            await update.message.reply_text("❌ Максимальное количество токенов: 4000")
            return
        
    except ValueError:
        await update.message.reply_text("❌ Некорректное значение. Используйте только числа.")
        return
    
    try:
        from config import write_max_tokens
        
        success = write_max_tokens(max_tokens)
        
        if success:
            await update.message.reply_text(
                f"✅ **Лимит токенов обновлен:**\n\n"
                f"🎯 Новый лимит: **{max_tokens} токенов**\n\n"
                f"Изменения вступят в силу для новых запросов к GPT.",
                parse_mode='Markdown'
            )
            logger.info(f"Админ {user_id} установил лимит токенов: {max_tokens}")
        else:
            await update.message.reply_text("❌ Ошибка при сохранении лимита токенов.")
            
    except Exception as e:
        logger.error(f"Ошибка команды /settokens: {e}")
        await update.message.reply_text("❌ Ошибка при установке лимита токенов.")

async def cmd_resettokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /resettokens - сбрасывает лимит токенов к значению по умолчанию
    Доступна только администраторам
    """
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        from config import reset_max_tokens, get_current_max_tokens
        import os
        
        success = reset_max_tokens()
        
        if success:
            current_tokens = get_current_max_tokens()
            default_tokens = int(os.getenv('MAX_TOKENS', 500))
            
            await update.message.reply_text(
                f"✅ **Лимит токенов сброшен к значению по умолчанию:**\n\n"
                f"🎯 Текущий лимит: **{current_tokens} токенов**\n"
                f"📋 Значение по умолчанию: **{default_tokens} токенов**\n\n"
                f"Изменения вступят в силу для новых запросов к GPT.",
                parse_mode='Markdown'
            )
            logger.info(f"Админ {user_id} сбросил лимит токенов к значению по умолчанию")
        else:
            await update.message.reply_text("❌ Ошибка при сбросе лимита токенов.")
            
    except Exception as e:
        logger.error(f"Ошибка команды /resettokens: {e}")
        await update.message.reply_text("❌ Ошибка при сбросе лимита токенов.")