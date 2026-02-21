# 📜 Bot Menu Contracts

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Contracts define the interfaces that the `bot_menu` feature uses to interact with the rest of the system. This ensures loose coupling and allows for easier testing and modification.

## 🏗️ Interface: MenuDiscoveryProvider

Located in: `src/telegram_bot/features/telegram/bot_menu/contracts/menu_contract.py`

The `BotMenuOrchestrator` depends on this protocol to retrieve the list of buttons that should be displayed on the dashboard.

### Methods

#### `get_menu_buttons() -> dict[str, dict]`
Returns a dictionary of all registered menu buttons.
- **Key**: Unique identifier of the feature.
- **Value**: Configuration dictionary (text, description, priority, access rules, etc.).

## 🧩 Implementation

In the production environment, this contract is implemented by the `FeatureDiscoveryService`.

The `FeatureDiscoveryService` scans all `INSTALLED_FEATURES`, reads their `MENU_CONFIG` from `feature_setting.py`, and aggregates them into the format expected by the `bot_menu`.

## 🧪 Mocking for Tests

Because the orchestrator depends on a protocol (Contract) rather than a concrete class, it is easy to provide a mock implementation for unit testing the menu logic without needing to load all project features.
