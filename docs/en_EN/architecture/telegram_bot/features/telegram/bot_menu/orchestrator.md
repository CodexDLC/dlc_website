# 📜 Bot Menu Orchestrator

[⬅️ Back](README.md) | [🏠 Docs Root](../../../../../../README.md)

Builds and renders the main dashboard by aggregating menu buttons from all registered features.

**File:** `src/telegram_bot/features/bot_menu/logic/orchestrator.py`

---

## 🏗️ Class: BotMenuOrchestrator

```text
BaseBotOrchestrator
  └── BotMenuOrchestrator
```

### Constructor

| Parameter | Type | Description |
|:---|:---|:---|
| `discovery_provider` | `MenuDiscoveryProvider` (Protocol) | Source of menu button configs |
| `settings` | `BotSettings` | For RBAC role checks |

Created **manually** in `BotContainer` (not via `feature_setting.py` factory) because it depends on `FeatureDiscoveryService`.

---

## 🔄 Render Flow

```text
render_menu(user_id)
│
├── 1. discovery.get_menu_buttons() → all feature configs
├── 2. For each config:
│       └── _check_access(user_id, config) → RBAC filter
├── 3. Collect available_features (passed RBAC)
└── 4. self.ui.render_dashboard(available_features)
        └── Returns UnifiedViewDTO(menu=ViewResultDTO)
```

---

## 🔐 RBAC Filtering

Each feature's `MENU_CONFIG` can declare access flags:

| Flag | Required Role | Description |
|:---|:---|:---|
| `is_superuser: True` | Superuser only | Developer/tech support features |
| `is_admin: True` | Owner or Superuser | Business admin features |
| *(no flags)* | Public | Available to all users |

```python
def _check_access(self, user_id: int, config: dict) -> bool:
    if config.get("is_superuser"):
        return user_id in self.settings.superuser_ids_list
    if config.get("is_admin"):
        return user_id in self.settings.owner_ids_list or \
               user_id in self.settings.superuser_ids_list
    return True
```

---

## 🖱️ Menu Click Handling

```text
handle_menu_click(target, user_id)
│
├── 1. Get target feature config
├── 2. Verify RBAC access
├── 3. Build CoreResponseDTO(next_state=target)
└── 4. self.process_response(response)
        └── Director.set_scene(target) → navigate to feature
```

---

## 📜 Contract: MenuDiscoveryProvider

```python
class MenuDiscoveryProvider(Protocol):
    def get_menu_buttons(self) -> dict[str, dict]: ...
```

Implemented by `FeatureDiscoveryService`.
