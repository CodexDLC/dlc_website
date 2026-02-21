from typing import TYPE_CHECKING

from loguru import logger as log

if TYPE_CHECKING:
    from src.telegram_bot.core.container import BotContainer

    from ..contracts.contract import NotificationsDataProvider


class NotificationsService:
    """
    Service layer for the Notifications feature.
    Encapsulates API calls, Redis Cache, and ARQ task enqueueing.
    TODO: Rename methods and adapt logic to your domain.
    """

    def __init__(self, container: "BotContainer", data_provider: "NotificationsDataProvider"):
        self.container = container
        self.data_provider = data_provider

    async def confirm_appointment(self, entity_id: int) -> dict:
        """Confirms the entity via Django API and triggers an email notification."""
        response = await self.data_provider.confirm_appointment(entity_id)

        if response.get("success"):
            await self.process_email_notification(entity_id, status="confirmed")

        return response

    async def cancel_appointment(self, entity_id: int, reason_code: str, reason_text: str) -> dict:
        """Cancels the entity via Django API and triggers an email notification."""
        response = await self.data_provider.cancel_appointment(
            appointment_id=entity_id, reason=reason_code, note=reason_text
        )

        if response.get("success"):
            await self.process_email_notification(entity_id, status="cancelled", reason_text=reason_text)

        return response

    async def process_email_notification(self, entity_id: int, status: str, reason_text: str | None = None):
        """Enqueues an email task via ARQ using cached Redis data."""
        if not self.container.arq_pool:
            log.error("ARQ pool not initialized.")
            return

        cache_manager = self.container.redis.appointment_cache
        entity_data = await cache_manager.get(entity_id)

        if not entity_data:
            log.warning(f"No cached data for entity {entity_id}. Email skipped.")
            return

        recipient_email = entity_data.get("client_email")
        if not recipient_email or recipient_email == "не указан":
            log.error(f"Invalid email for entity {entity_id}.")
            return

        from ..ui.ui import NotificationsUI

        ui = NotificationsUI()
        email_data = ui.render_email_data(entity_data, status, reason_text)

        try:
            await self.container.arq_pool.enqueue_job(
                # TODO: Replace "send_email_task" with your ARQ task name
                "send_email_task",
                recipient_email=recipient_email,
                subject=email_data.get("email_subject"),
                template_name="confirmation.html" if status == "confirmed" else "cancellation.html",
                data=email_data,
            )
            log.info(f"Email task enqueued for {recipient_email}")
            await cache_manager.delete(entity_id)
        except Exception as e:
            log.error(f"Failed to enqueue email task: {e}")
