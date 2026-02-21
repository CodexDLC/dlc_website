from loguru import logger as log

# Import BaseApiClient from core
from src.telegram_bot.core.api_client import BaseApiClient
from src.telegram_bot.features.telegram.notifications.contracts.contract import NotificationsDataProvider


class NotificationsApiProvider(NotificationsDataProvider):
    """
    API Provider for managing domain events via Django API.
    Encapsulates endpoints and interaction with the backend.
    TODO: Replace with your domain API endpoints and logic.
    """

    # TODO: Replace with your domain API endpoint
    ENDPOINT = "/api/v1/events/manage/"

    def __init__(self, api_client: BaseApiClient):
        self.api_client = api_client

    async def confirm_appointment(self, appointment_id: int) -> dict:
        """
        Confirm an event entity via Django API.
        TODO: Rename and adapt to your domain action.
        """
        log.debug(f"NotificationsApiProvider | Confirming entity_id={appointment_id}")
        return await self.api_client._request(
            method="POST",
            endpoint=self.ENDPOINT,
            json={"entity_id": appointment_id, "action": "confirm"},
        )

    async def cancel_appointment(self, appointment_id: int, reason: str | None = None, note: str | None = None) -> dict:
        """
        Reject/cancel an event entity via Django API.
        TODO: Rename and adapt to your domain action.
        """
        log.debug(f"NotificationsApiProvider | Cancelling entity_id={appointment_id} reason={reason}")
        return await self.api_client._request(
            method="POST",
            endpoint=self.ENDPOINT,
            json={"entity_id": appointment_id, "action": "cancel", "cancel_reason": reason, "cancel_note": note},
        )
