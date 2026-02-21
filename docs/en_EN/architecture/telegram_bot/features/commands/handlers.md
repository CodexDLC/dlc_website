# 📜 Commands Handlers

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Thin handlers that route Telegram updates to orchestrators and send responses.

**File:** `src/telegram_bot/features/commands/handlers/router.py`

---

## 📋 Registered Commands

| Command | Handler | Description |
|:---|:---|:---|
| `/start` | `cmd_start` | Welcome screen + user sync |
| `/help` | `cmd_help` | Help text with available commands |
| `/get_ids` | `cmd_get_ids` | Debug: shows user and chat IDs |
| `SettingsCallback` | `handle_settings_callback` | Inline button for settings (WIP) |

---

## 🔄 /start Flow

```text
1. Telegram sends /start
2. Handler saves old FSM state data (snapshot)
3. FSM state is fully cleared
4. /start message is deleted from chat
5. Orchestrator fetched from container.features["commands"]
6. orchestrator.handle_entry(user_id, payload=User)
7. ViewSender sends the resulting UnifiedViewDTO
```

### Key Pattern: Snapshot & Clean

Before clearing FSM, we save current state data. This allows `ViewSender` to find and delete previous interface messages (stored as message IDs in state data).

---

## 🧩 Handler Anatomy

Every handler follows the same pattern:

```python
async def handler(update, state, bot, container: BotContainer):
    # 1. Get orchestrator from container
    orchestrator = container.features["feature_key"]

    # 2. Call business logic
    view_dto = await orchestrator.handle_entry(user_id, payload)

    # 3. Send response
    sender = ViewSender(bot, state, old_state_data, user_id)
    await sender.send(view_dto)
```

Handlers contain **zero business logic**. All decisions happen in the orchestrator.
