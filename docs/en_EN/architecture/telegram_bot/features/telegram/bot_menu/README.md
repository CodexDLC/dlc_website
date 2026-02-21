# 📂 Bot Menu (Dashboard)

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../../README.md)

The `bot_menu` feature is the central hub (Dashboard) of the Telegram Bot. It provides a persistent interface with buttons that allow users to navigate between different installed features.

## 🏗️ Architecture

Located in: `src/telegram_bot/features/telegram/bot_menu`

### Orchestrator: `BotMenuOrchestrator`
The core logic coordinator for the dashboard.
- **Discovery**: Uses `MenuDiscoveryProvider` to find all installed features that want to appear in the menu.
- **Access Control**: Filters buttons based on user roles (Superuser, Admin, Owner) defined in `BotSettings`.
- **Navigation**: Handles menu clicks and directs the user to the target feature's state.

### UI: `BotMenuUI`
Responsible for rendering the dashboard message and keyboard.
- **Dynamic Keyboard**: Buttons are generated dynamically based on the `MENU_CONFIG` of other features.

## 📋 feature_setting.py

```python
class BotMenuStates(StatesGroup):
    main = State()

STATES = BotMenuStates
GARBAGE_COLLECT = True
```

## 🔄 Logic Flow

1.  **Entry**: User triggers the menu (e.g., via `/start` or a "Back to Menu" button).
2.  **Discovery**: Orchestrator asks `FeatureDiscoveryService` for all registered menu buttons.
3.  **Filtering**: Orchestrator checks the user's ID against `superuser_ids` and `owner_ids`.
4.  **Rendering**: `BotMenuUI` creates a keyboard with the allowed buttons.
5.  **Navigation**: When a button is clicked, the orchestrator returns a `UnifiedViewDTO` that triggers a state transition in the bot.

## 🧩 Menu Integration

Other features appear in this menu by defining a `MENU_CONFIG` in their own `feature_setting.py`. The `bot_menu` itself does not need to be modified to add new buttons.
