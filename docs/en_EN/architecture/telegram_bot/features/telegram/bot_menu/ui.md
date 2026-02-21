# 🎨 Bot Menu UI (Rendering)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `BotMenuUI` is a pure rendering layer. It takes raw data (feature configurations) and transforms it into a `ViewResultDTO` containing the text and keyboard for the Telegram message.

## 🏗️ Class: BotMenuUI

Located in: `src/telegram_bot/features/telegram/bot_menu/ui/menu_ui.py`

### Methods

#### `render_dashboard(buttons: dict[str, dict]) -> ViewResultDTO`

Generates the main dashboard interface.

- **Input**: A dictionary of feature configurations (text, callback_data, priority, etc.).
- **Process**:
    1.  Initializes an `InlineKeyboardBuilder`.
    2.  Iterates through the provided buttons.
    3.  If a button has explicit `callback_data`, it uses it. Otherwise, it generates a `DashboardCallback` with a `nav` action.
    4.  Adjusts the keyboard layout (currently 2 buttons per row).
- **Output**: A `ViewResultDTO` containing the `DASHBOARD_TITLE` and the generated inline keyboard.

## 🧩 Components

### Keyboard Builder
The UI uses `aiogram.utils.keyboard.InlineKeyboardBuilder` for flexible keyboard construction.

### Callbacks
Navigation buttons use the `DashboardCallback` schema:
- **action**: `nav` (navigation)
- **target**: The key of the target feature (e.g., `booking`, `account`).

## 📝 Design Principles

- **Stateless**: The UI layer does not store any state or perform any API calls.
- **Decoupled**: It doesn't know which features are installed; it simply renders whatever buttons the orchestrator provides.
