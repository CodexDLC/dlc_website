from pydantic import BaseModel


class EventNotificationPayload(BaseModel):
    """
    Generic payload for domain event notifications received from Redis stream.
    TODO: Replace/extend with your domain-specific fields.

    Example usage:
        payload = EventNotificationPayload(
            event_type="order_created",
            entity_id=42,
            title="New order #42",
            description="Customer: John Doe",
            extra={"amount": "100.00", "currency": "USD"},
        )
    """

    event_type: str  # e.g. "example_event", "order_created", "user_registered"
    entity_id: str | int | None = None
    title: str | None = None
    description: str | None = None
    # TODO: Add your domain-specific fields here
    extra: dict = {}
