class SenderKeys:
    """
    Ключи для SenderManager.
    """

    @staticmethod
    def get_user_coords_key(user_id: int | str) -> str:
        """
        Ключ для хранения координат UI пользователя (личка).
        Тип: HASH
        Пример: sender:user:123456789
        """
        return f"sender:user:{user_id}"

    @staticmethod
    def get_channel_coords_key(session_id: str) -> str:
        """
        Ключ для хранения координат UI канала/группы.
        Тип: HASH
        Пример: sender:channel:booking_feed_1
        """
        return f"sender:channel:{session_id}"
