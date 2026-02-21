# 🧠 Bot Menu Logic (Orchestrator)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The business logic of the Dashboard is encapsulated in the `BotMenuOrchestrator`. It acts as a coordinator between the feature discovery system and the UI.

## 🏗️ Class: BotMenuOrchestrator

Located in: `src/telegram_bot/features/telegram/bot_menu/logic/orchestrator.py`

### Responsibilities

1.  **Menu Assembly**: Fetches all available feature configurations via the `MenuDiscoveryProvider`.
2.  **Access Control**: Validates if the current user has the required permissions (Admin/Superuser) to see specific menu buttons.
3.  **Navigation Handling**: Processes menu clicks and prepares the system for a state transition to the target feature.

### Key Methods

#### `render_menu(user_id: int)`
The primary method for generating the dashboard view.
- **Step 1**: Retrieves all registered menu buttons from the discovery service.
- **Step 2**: Filters buttons based on the user's role (checked against `BotSettings`).
- **Step 3**: Calls the UI layer to render the final `UnifiedViewDTO`.

#### `handle_menu_click(target: str, user_id: int)`
Handles the interaction when a user clicks a dashboard button.
- Validates access to the target feature.
- Returns a `UnifiedViewDTO` with a `next_state` header, which the `ViewSender` uses to transition the user's FSM state.

#### `_check_access(user_id: int, config: dict)` (Internal)
A helper method that implements the security logic:
- **is_superuser**: Checks if the user ID is in the `superuser_ids_list`.
- **is_admin**: Checks if the user is either an owner or a superuser.
- **Default**: Access is granted to everyone.

## 🔄 State Management

The `bot_menu` typically operates in the `BotMenuStates.main` state. When a user navigates to another feature, the orchestrator provides the new state name, and the `Director` (or handler) updates the FSM context.
