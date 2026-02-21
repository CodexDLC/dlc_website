from typing import Any

from loguru import logger as log

from src.telegram_bot.services.redis.router import RedisRouter

# Create router for notifications
notifications_router = RedisRouter()


# TODO: Replace "example_event" with your domain event type (e.g. "order_created", "user_registered")
@notifications_router.message("example_event")
async def handle_new_event_notification(message_data: dict[str, Any], container: Any):
    """
    Handler for a new domain event notification from Redis stream.
    TODO: Rename this handler and adapt the logic to your domain.
    """
    try:
        orchestrator = container.redis_notifications
        view_sender = container.view_sender
        cache_manager = container.redis.appointment_cache

        entity_id = message_data.get("id") or message_data.get("entity_id")
        log.info(f"Notifications | Processing event. ID={entity_id}")

        # 1. Cache event data in Redis for later use in UI feature
        if entity_id:
            await cache_manager.save(entity_id, message_data)
            log.debug(f"Notifications | Event {entity_id} cached in Redis.")

        # 2. Try to process normally (build UnifiedViewDTO)
        try:
            view_dto = orchestrator.handle_notification(message_data)
        except Exception as e:
            log.error(f"Notifications | Orchestrator failed: {e}")
            # 3. If failed — send fallback notification
            view_dto = orchestrator.handle_failure(message_data, str(e))

        # 4. Send notification to Telegram
        await view_sender.send(view_dto)

    except Exception as e:
        log.critical(f"Notifications | Fatal error in handler: {e}")
