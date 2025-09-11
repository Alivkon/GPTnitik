"""
Модуль для управления пользователями с истекшим периодом эксплуатации
"""
import csv
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Set, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Путь к CSV файлу с заблокированными пользователями
BLOCKED_USERS_FILE = Path('data/blocked_users.csv')

@dataclass
class BlockedUser:
    """Информация о заблокированном пользователе"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    blocked_at: datetime
    reason: str
    message_count: int = 0
    session_duration: int = 0  # в минутах

class UserLimitManager:
    """Менеджер для управления пользователями с истекшим периодом эксплуатации"""
    
    def __init__(self):
        self._blocked_users: Set[int] = set()
        self._load_blocked_users()
    
    def _load_blocked_users(self) -> None:
        """Загружает список заблокированных пользователей из CSV файла"""
        try:
            if not BLOCKED_USERS_FILE.exists():
                # Создаем файл с заголовками
                self._create_csv_file()
                return
            
            with open(BLOCKED_USERS_FILE, 'r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        user_id = int(row['user_id'])
                        self._blocked_users.add(user_id)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Некорректная строка в CSV: {row}, ошибка: {e}")
            
            logger.info(f"Загружено {len(self._blocked_users)} заблокированных пользователей")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки заблокированных пользователей: {e}")
            self._blocked_users = set()
    
    def _create_csv_file(self) -> None:
        """Создает CSV файл с заголовками"""
        try:
            # Создаем директорию если не существует
            BLOCKED_USERS_FILE.parent.mkdir(exist_ok=True)
            
            with open(BLOCKED_USERS_FILE, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'user_id', 'username', 'first_name', 'blocked_at', 
                    'reason', 'message_count', 'session_duration'
                ])
            
            logger.info(f"Создан файл заблокированных пользователей: {BLOCKED_USERS_FILE}")
            
        except Exception as e:
            logger.error(f"Ошибка создания CSV файла: {e}")
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Проверяет, заблокирован ли пользователь"""
        return user_id in self._blocked_users
    
    def block_user(self, user_id: int, username: Optional[str] = None, 
                   first_name: Optional[str] = None, reason: str = "Превышен лимит", 
                   message_count: int = 0, session_duration: int = 0) -> bool:
        """
        Блокирует пользователя и записывает в CSV файл
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя в Telegram
            first_name: Имя пользователя
            reason: Причина блокировки
            message_count: Количество сообщений в сессии
            session_duration: Длительность сессии в минутах
        
        Returns:
            True если пользователь успешно заблокирован, False в случае ошибки
        """
        try:
            # Добавляем в память
            self._blocked_users.add(user_id)
            
            # Записываем в CSV файл
            blocked_user = BlockedUser(
                user_id=user_id,
                username=username,
                first_name=first_name,
                blocked_at=datetime.now(),
                reason=reason,
                message_count=message_count,
                session_duration=session_duration
            )
            
            # Проверяем существование файла
            if not BLOCKED_USERS_FILE.exists():
                self._create_csv_file()
            
            # Добавляем запись в файл
            with open(BLOCKED_USERS_FILE, 'a', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    blocked_user.user_id,
                    blocked_user.username or '',
                    blocked_user.first_name or '',
                    blocked_user.blocked_at.isoformat(),
                    blocked_user.reason,
                    blocked_user.message_count,
                    blocked_user.session_duration
                ])
            
            logger.info(f"Пользователь {user_id} ({first_name}) заблокирован. Причина: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка блокировки пользователя {user_id}: {e}")
            return False
    
    def unblock_user(self, user_id: int) -> bool:
        """
        Разблокирует пользователя (удаляет из списка и перезаписывает CSV файл)
        
        Args:
            user_id: ID пользователя для разблокировки
        
        Returns:
            True если пользователь успешно разблокирован, False в случае ошибки
        """
        try:
            if user_id not in self._blocked_users:
                logger.warning(f"Пользователь {user_id} не найден в списке заблокированных")
                return False
            
            # Удаляем из памяти
            self._blocked_users.remove(user_id)
            
            # Перезаписываем CSV файл без этого пользователя
            if not BLOCKED_USERS_FILE.exists():
                logger.warning("CSV файл не существует")
                return True
            
            # Читаем все записи кроме удаляемой
            rows_to_keep = []
            with open(BLOCKED_USERS_FILE, 'r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        if int(row['user_id']) != user_id:
                            rows_to_keep.append(row)
                    except (ValueError, KeyError):
                        # Сохраняем некорректные строки
                        rows_to_keep.append(row)
            
            # Перезаписываем файл
            with open(BLOCKED_USERS_FILE, 'w', encoding='utf-8', newline='') as file:
                if rows_to_keep:
                    fieldnames = rows_to_keep[0].keys()
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows_to_keep)
                else:
                    # Если файл стал пустым, создаем с заголовками
                    writer = csv.writer(file)
                    writer.writerow([
                        'user_id', 'username', 'first_name', 'blocked_at', 
                        'reason', 'message_count', 'session_duration'
                    ])
            
            logger.info(f"Пользователь {user_id} разблокирован")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка разблокировки пользователя {user_id}: {e}")
            return False
    
    def get_blocked_users_count(self) -> int:
        """Возвращает количество заблокированных пользователей"""
        return len(self._blocked_users)
    
    def get_blocked_users_info(self) -> list:
        """
        Во��вращает информацию о всех заблокированных пользователях
        
        Returns:
            Список словарей с информацией о заблокированных пользователях
        """
        try:
            if not BLOCKED_USERS_FILE.exists():
                return []
            
            users_info = []
            with open(BLOCKED_USERS_FILE, 'r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        # Парсим дату
                        blocked_at = datetime.fromisoformat(row['blocked_at'])
                        
                        users_info.append({
                            'user_id': int(row['user_id']),
                            'username': row.get('username', ''),
                            'first_name': row.get('first_name', ''),
                            'blocked_at': blocked_at,
                            'reason': row.get('reason', ''),
                            'message_count': int(row.get('message_count', 0)),
                            'session_duration': int(row.get('session_duration', 0))
                        })
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Некорректная строка в CSV: {row}, ошибка: {e}")
            
            return users_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о заблокированных пользователях: {e}")
            return []
    
    def check_user_limits(self, user_id: int, message_count: int, session_duration_minutes: int,
                         username: Optional[str] = None, first_name: Optional[str] = None) -> bool:
        """
        Проверяет лимиты пользователя и блокирует при превышении
        
        Args:
            user_id: ID пользователя
            message_count: Количество сообщений в текущей сессии
            session_duration_minutes: Длительность сессии в минутах
            username: Имя пользователя в Telegram
            first_name: Имя пользователя
        
        Returns:
            True если пользователь должен быть заблокирован, False если все в порядке
        """
        from config import MAX_MESSAGES_PER_SESSION, SESSION_DURATION_MINUTES
        
        # Проверяем лимит сообщений
        if message_count >= MAX_MESSAGES_PER_SESSION:
            reason = f"Превышен лимит сообщений ({MAX_MESSAGES_PER_SESSION})"
            self.block_user(user_id, username, first_name, reason, message_count, session_duration_minutes)
            return True
        
        # Проверяем лимит времени
        if session_duration_minutes >= SESSION_DURATION_MINUTES:
            reason = f"Превышен лимит времени ({SESSION_DURATION_MINUTES} мин)"
            self.block_user(user_id, username, first_name, reason, message_count, session_duration_minutes)
            return True
        
        return False
    
    def cleanup_old_blocks(self, days_old: int = 30) -> int:
        """
        Удаляет старые блокировки (старше указанного количества дней)
        
        Args:
            days_old: Количество дней, после которых блокировка считается старой
        
        Returns:
            Количество удаленных записей
        """
        try:
            if not BLOCKED_USERS_FILE.exists():
                return 0
            
            cutoff_date = datetime.now() - timedelta(days=days_old)
            rows_to_keep = []
            removed_count = 0
            
            with open(BLOCKED_USERS_FILE, 'r', encoding='utf-8', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        blocked_at = datetime.fromisoformat(row['blocked_at'])
                        if blocked_at >= cutoff_date:
                            rows_to_keep.append(row)
                        else:
                            # Удаляем из памяти
                            user_id = int(row['user_id'])
                            self._blocked_users.discard(user_id)
                            removed_count += 1
                    except (ValueError, KeyError):
                        # Сохраняем некорректные строки
                        rows_to_keep.append(row)
            
            # Перезаписываем файл
            with open(BLOCKED_USERS_FILE, 'w', encoding='utf-8', newline='') as file:
                if rows_to_keep:
                    fieldnames = rows_to_keep[0].keys()
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows_to_keep)
                else:
                    # Если файл стал пустым, создаем с заголовками
                    writer = csv.writer(file)
                    writer.writerow([
                        'user_id', 'username', 'first_name', 'blocked_at', 
                        'reason', 'message_count', 'session_duration'
                    ])
            
            logger.info(f"Удалено {removed_count} старых блокировок (старше {days_old} дней)")
            return removed_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки старых блокировок: {e}")
            return 0
    
    def clear_all_blocks(self) -> int:
        """
        Полностью очищает все блокировки (сброс в 00:00)
        
        Returns:
            Количество удаленных записей
        """
        try:
            if not BLOCKED_USERS_FILE.exists():
                return 0
            
            # Подсчитываем количество заблокированных пользователей
            blocked_count = len(self._blocked_users)
            
            # Очищаем память
            self._blocked_users.clear()
            
            # Создаем пустой файл с заголовками
            self._create_csv_file()
            
            logger.info(f"Выполнена полная очистка блокировок: удалено {blocked_count} записей")
            return blocked_count
            
        except Exception as e:
            logger.error(f"Ошибка полной очистки блокировок: {e}")
            return 0

# Глобальный экземпляр менеджера
user_limit_manager = UserLimitManager()