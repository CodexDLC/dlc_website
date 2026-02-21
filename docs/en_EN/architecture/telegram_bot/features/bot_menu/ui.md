# 📜 Bot Menu UI

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Pure rendering layer for the dashboard screen.

**File:** `src/telegram_bot/features/bot_menu/ui/menu_ui.py`

---

## 🏗️ Class: BotMenuUI

### render_dashboard(features: dict) → ViewResultDTO

Takes a dictionary of available features (already filtered by RBAC) and builds:

- **Text:** Dashboard title from `resources/texts.py`
- **Keyboard:** One inline button per feature, sorted by `priority`

Each button uses `DashboardCallback(target=feature_key)` for navigation.

---

## 🎨 Button Layout

Buttons are rendered from `MENU_CONFIG` of each feature:

```python
MENU_CONFIG = {
    "key": "commands",
    "text": "🛠 Commands",       # Button label
    "description": "...",         # Shown in dashboard text
    "target_state": "commands",   # Director navigation key
    "priority": 100,              # Sort order (lower = higher)
}
```

Features without `MENU_CONFIG` (like `errors`) do not appear in the dashboard.
