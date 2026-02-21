from src.workers.core.tasks import CORE_FUNCTIONS

from .email_tasks import send_email_task
from .notification_tasks import requeue_event_task, send_domain_event_task

# Агрегируем все задачи воркера.
# ARQ регистрирует функции из этого списка — только они доступны для вызова через enqueue_job().
# Добавляй свои задачи сюда по мере разработки проекта.

FUNCTIONS = [
    send_domain_event_task,  # TODO: Replace with your domain tasks
    send_email_task,
    requeue_event_task,
] + CORE_FUNCTIONS
