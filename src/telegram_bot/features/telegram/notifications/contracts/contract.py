from typing import Protocol


class NotificationsDataProvider(Protocol):
    """
    Контракт для доступа к данным фичи Notifications.
    """

    async def confirm_appointment(self, appointment_id: int) -> dict:
        """Подтвердить заявку."""
        ...

    async def cancel_appointment(self, appointment_id: int, reason: str | None = None, note: str | None = None) -> dict:
        """Отклонить заявку."""
        ...
