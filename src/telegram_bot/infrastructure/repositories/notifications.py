from collections.abc import Callable
from typing import Any

# from sqlalchemy import select, insert, update, delete # Для CRUD, если понадобится
from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncSession

from src.telegram_bot.features.telegram.notifications.contracts.contract import NotificationsDataProvider

# --- Здесь должна быть импортирована ваша реальная модель Notification ---
# Например: from src.telegram_bot.infrastructure.models.notification import Notification
# Или: from src.telegram_bot.infrastructure.models import Notification # Если она в __init__.py

# --- Заглушка класса Notification удалена ---


class NotificationsRepositoryProvider(NotificationsDataProvider):
    """
    Реализация NotificationsDataProvider, использующая прямое подключение к БД (SQLAlchemy).
    """

    def __init__(self, session_factory: Callable[..., AsyncSession]):
        self.session_factory = session_factory

    async def get_data(self, user_id: int) -> Any:
        """
        Пример метода получения данных из БД (CRUD - Read).
        """
        log.debug(f"NotificationsRepositoryProvider | Fetching data for user_id={user_id} via Repository")
        # async with self.session_factory() as session: # <-- Закомментировано
        # Здесь будет реальный запрос к базе данных, например:
        # result = await session.execute(select(Notification).filter_by(user_id=user_id))
        # notifications = result.scalars().all()
        # return [n.to_dict() for n in notifications]
        return {"message": f"Data from Repository for user {user_id}", "notifications": []}  # Заглушка

    async def create_notification(self, user_id: int, data: dict) -> Any:
        """
        Заглушка для создания уведомления в БД (CRUD - Create).
        """
        log.debug(f"NotificationsRepositoryProvider | Creating notification for user_id={user_id} via Repository")
        # async with self.session_factory() as session: # <-- Закомментировано
        #     stmt = insert(Notification).values(user_id=user_id, message=data.get("message")).returning(Notification)
        #     result = await session.execute(stmt)
        #     await session.commit()
        #     return result.scalar_one().to_dict()
        return {"message": f"Notification created for user {user_id}", "data": data}

    async def update_notification(self, notification_id: int, data: dict) -> Any:
        """
        Заглушка для обновления уведомления в БД (CRUD - Update).
        """
        log.debug(f"NotificationsRepositoryProvider | Updating notification_id={notification_id} via Repository")
        # async with self.session_factory() as session: # <-- Закомментировано
        #     stmt = update(Notification).filter_by(id=notification_id).values(**data).returning(Notification)
        #     result = await session.execute(stmt)
        #     await session.commit()
        #     return result.scalar_one().to_dict()
        return {"message": f"Notification {notification_id} updated", "data": data}

    async def delete_notification(self, notification_id: int) -> None:
        """
        Заглушка для удаления уведомления из БД (CRUD - Delete).
        """
        log.debug(f"NotificationsRepositoryProvider | Deleting notification_id={notification_id} via Repository")
        # async with self.session_factory() as session: # <-- Закомментировано
        #     stmt = delete(Notification).filter_by(id=notification_id)
        #     await session.execute(stmt)
        #     await session.commit()
        return
