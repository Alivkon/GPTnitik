"""
Модуль планировщика задач для автоматического выполнения операций
"""
import asyncio
import logging
from datetime import datetime, time
from typing import Optional

logger = logging.getLogger(__name__)

class DailyScheduler:
    """Планировщик для выполнения задач в определенное время каждый день"""
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запускает планировщик"""
        if self._running:
            logger.warning("Планировщик уже запущен")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Планировщик задач запущен")
    
    async def stop(self):
        """Останавливает планировщик"""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Планировщик задач остановлен")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика"""
        try:
            while self._running:
                # Вычисляем время до следующего выполнения (00:00)
                now = datetime.now()
                target_time = time(0, 0)  # 00:00
                
                # Если сейчас уже после 00:00, планируем на следующий день
                if now.time() > target_time:
                    next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    next_run = next_run.replace(day=next_run.day + 1)
                else:
                    next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Вычисляем время ожидания
                wait_seconds = (next_run - now).total_seconds()
                
                logger.info(f"Следующая очистка блокировок запланирована на: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"Ожидание: {wait_seconds:.0f} секунд ({wait_seconds/3600:.1f} часов)")
                
                # Ждем до назначенного времени
                await asyncio.sleep(wait_seconds)
                
                if self._running:
                    await self._execute_daily_cleanup()
                
        except asyncio.CancelledError:
            logger.info("Планировщик задач отменен")
        except Exception as e:
            logger.error(f"Ошибка в планировщике задач: {e}")
    
    async def _execute_daily_cleanup(self):
        """Выполняет ежедневную очистку блокировок в 00:00"""
        try:
            logger.info("🕛 Выполняется ежедневная очистка заблокированных пользователей (00:00)")
            
            from user_limits import user_limit_manager
            
            # Получаем количество заблокированных пользователей до очистки
            blocked_count_before = user_limit_manager.get_blocked_users_count()
            
            # Выполняем полную очистку
            cleared_count = user_limit_manager.clear_all_blocks()
            
            # Логируем результат
            if cleared_count > 0:
                logger.info(f"✅ Ежедневная очистка завершена: разблокировано {cleared_count} пользователей")
                
                # Отправляем уведомление администраторам
                await self._notify_admins_about_cleanup(cleared_count)
            else:
                logger.info("ℹ️ Ежедневная очистка завершена: заблокированных пользователей не было")
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении ежедневной очистки: {e}")
    
    async def _notify_admins_about_cleanup(self, cleared_count: int):
        """Отправляет уведомление администраторам о выполненной очистке"""
        try:
            from utils import send_to_admins_text
            
            message = (
                f"🕛 **Ежедневная очистка блокировок (00:00)**\n\n"
                f"✅ Разблокировано пользователей: **{cleared_count}**\n"
                f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n"
                f"Все пользователи снова могут пользоваться ботом."
            )
            
            # Отправляем уведомление (если функция существует)
            try:
                await send_to_admins_text(message)
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление администраторам: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления администраторам: {e}")

# Глобальный экземпляр планировщика
daily_scheduler = DailyScheduler()