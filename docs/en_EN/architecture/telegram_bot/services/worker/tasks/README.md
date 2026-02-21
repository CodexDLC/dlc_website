# 📂 Background Tasks

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../../README.md)

Task definitions for the ARQ background worker.

---

## 📋 Available Tasks

| Task | File | Description |
|:---|:---|:---|
| `send_notification_task` | `notifications.py` | Send a message to a specific user |

---

## 🔧 Adding a New Task

1. Create a new file in `services/worker/tasks/`
2. Define an async function with `ctx: dict` as first parameter
3. Register it in `BotArqSettings.functions` list
4. Export it from `tasks/__init__.py`

```python
# services/worker/tasks/my_task.py
async def my_task(ctx: dict, user_id: int, data: str):
    bot = ctx["bot"]
    await bot.send_message(user_id, data)
```

---

## 🔗 Enqueueing Tasks

From handlers or orchestrators:

```python
from arq.connections import ArqRedis

pool: ArqRedis = ...  # Get from container
await pool.enqueue_job("send_notification_task", user_id=123, message="Hello!")
```
