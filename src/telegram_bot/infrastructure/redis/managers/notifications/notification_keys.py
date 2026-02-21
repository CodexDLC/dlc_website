class NotificationKeys:
    """
    Redis key definitions for the notifications feature.
    TODO: Change PREFIX to match your domain if needed.
    """

    PREFIX = "notification"  # TODO: Change prefix to match your domain

    @classmethod
    def get_cache_key(cls, entity_id: int | str) -> str:
        """
        Key for temporary storage of entity data (JSON).
        Example: notification:cache:123
        """
        return f"{cls.PREFIX}:cache:{entity_id}"

    @classmethod
    def get_pending_key(cls, entity_id: int | str) -> str:
        """
        Key for pending notification state.
        Example: notification:pending:123
        """
        return f"{cls.PREFIX}:pending:{entity_id}"

    # Backward-compatible alias
    @staticmethod
    def get_appointment_cache_key(appointment_id: int | str) -> str:
        return NotificationKeys.get_cache_key(appointment_id)
