class RedisStreams:
    """
    Константы для Redis Streams.
    Определяют имена стримов и групп потребителей.
    """

    class BotEvents:
        """Стрим для событий, которые должен обработать Бот (уведомления, команды)."""

        NAME = "bot_events"
        GROUP = "bot_group"
        # Префикс для имени потребителя (добавляется hostname или uuid)
        CONSUMER_PREFIX = "bot_instance_"

    # Пример будущего стрима
    # class EmailEvents:
    #     NAME = "email_events"
    #     GROUP = "email_workers"
