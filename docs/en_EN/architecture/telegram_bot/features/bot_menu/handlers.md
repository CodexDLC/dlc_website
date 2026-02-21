# 📜 Bot Menu Handlers

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Handles the `/menu` command and dashboard navigation callbacks.

**File:** `src/telegram_bot/features/bot_menu/handlers/menu_handlers.py`

---

## 📋 Registered Handlers

| Trigger | Handler | Description |
|:---|:---|:---|
| `/menu` command | `cmd_menu` | Renders the dashboard |
| `DashboardCallback` | `on_menu_nav` | Navigates to selected feature |

---

## 🔄 Navigation Flow

```text
User clicks feature button
  → on_menu_nav(call, callback_data)
    → orchestrator.handle_menu_click(target, user_id)
      → CoreResponseDTO(next_state=target)
        → process_response → Director.set_scene(target)
          → Target feature's handle_entry()
```

The menu handler does not directly call other features. It delegates navigation to the Director through `process_response`.
