# 📜 Bot Worker

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

ARQ worker configuration for the Telegram bot's background tasks.

**File:** `src/telegram_bot/services/worker/bot_worker.py`

---

## 🎯 Purpose

Some operations should not block the handler (e.g., sending bulk notifications, scheduled messages). The ARQ worker runs as a separate process and executes these tasks asynchronously via Redis queue.

---

## 🏗️ Class: BotArqSettings

Extends `BaseArqSettings` from `shared/core/arq/base.py`:

| Setting | Description |
|:---|:---|
| `redis_settings` | Redis connection for the job queue |
| `on_startup` | `bot_startup()` — creates Bot instance |
| `on_shutdown` | `bot_shutdown()` — closes Bot session |
| `functions` | List of registered task functions |

---

## 🔄 Lifecycle

```text
Worker process starts
  → bot_startup(ctx)
    → base_startup(ctx)  (shared ARQ initialization)
    → Bot(token=settings.bot_token)
    → ctx["bot"] = bot

Worker receives task
  → task_function(ctx, **kwargs)
    → ctx["bot"].send_message(...)

Worker process stops
  → bot_shutdown(ctx)
    → bot.session.close()
    → base_shutdown(ctx)
```

---

## 🚀 Running the Worker

```bash
arq src.telegram_bot.services.worker.bot_worker.BotArqSettings
```

The worker runs independently from the main polling process. It needs its own Bot instance because it is a separate process.
