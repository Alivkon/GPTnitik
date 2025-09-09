"""
Модуль для административных команд
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import is_admin, read_prompt, write_prompt, reset_prompt

##logger = logging.getLogger(__name__)

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
        
        #logger.info(f"Админ {user_id} запросил текущий промпт")
        
    except Exception as e:
        #logger.error(f"Ошибка команды /prompt: {e}")
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
            #logger.info(f"Админ {user_id} обновил промпт: {new_prompt[:50]}...")
        else:
            await update.message.reply_text("❌ Ошибка при сохранении промпта.")
            
    except Exception as e:
        #logger.error(f"Ошибка команды /setprompt: {e}")
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
            #logger.info(f"Админ {user_id} сбросил промпт к значению по умолчанию")
        else:
            await update.message.reply_text("❌ Ошибка при сбросе промпта.")
            
    except Exception as e:
        #logger.error(f"Ошибка команды /resetprompt: {e}")
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
        from config import DEBUG_SEND_VOICE, ADMIN_IDS
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
        
        stats_message = f"""📊 **Статистика бота:**

🔧 **Настройки:**
• DEBUG_SEND_VOICE: {DEBUG_SEND_VOICE}
• Администраторов: {len([aid for aid in ADMIN_IDS if aid != 0])}

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
        
        #logger.info(f"Админ {user_id} запросил статистику")
        
    except Exception as e:
        #logger.error(f"Ошибка команды /stats: {e}")
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
        #logger.info(f"Админ {user_id} запустил очистку временных файлов")
        
    except Exception as e:
        #logger.error(f"Ошибка команды /cleanup: {e}")
        await update.message.reply_text("❌ Ошибка при очистке файлов.")