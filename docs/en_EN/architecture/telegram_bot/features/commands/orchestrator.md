# 📜 Commands Orchestrator

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Coordinates the `/start` flow: syncs user data via contract, then renders the welcome screen.

**File:** `src/telegram_bot/features/commands/logic/orchestrator.py`

---

## 🏗️ Class: StartOrchestrator

```text
BaseBotOrchestrator
  └── StartOrchestrator
```

### Constructor

| Parameter | Type | Description |
|:---|:---|:---|
| `auth_provider` | `AuthDataProvider` (Protocol) | Data access layer (API or DB) |
| `ui` | `CommandsUI` | Pure UI renderer |

Created as a **singleton** by the factory in `feature_setting.py`. The `User` object is passed at call time, not at construction.

---

## 🔄 Entry Flow

```text
handle_entry(user_id, payload=User)
│
├── 1. Extract User from payload
├── 2. Build UserUpsertDTO (telegram_id, first_name, username, ...)
├── 3. await self.auth.upsert_user(user_dto)  ← Contract call
├── 4. user_name = user.first_name or "User"
└── 5. return await self.render(user_name)
         └── self.ui.render_start_screen(user_name)
             └── Returns UnifiedViewDTO(menu=ViewResultDTO, content=None)
```

---

## 📜 Contract: AuthDataProvider

```python
class AuthDataProvider(Protocol):
    async def upsert_user(self, user_dto: UserUpsertDTO) -> None: ...
    async def logout(self, user_id: int) -> None: ...
```

**API Mode:** Implemented by `AuthClient` (HTTP calls to FastAPI backend).
**Direct Mode:** Would be implemented by `AuthRepository` (SQLAlchemy queries).

---

## 🎨 UI: CommandsUI

Pure transformation layer. Takes data, returns `ViewResultDTO`.

```python
class CommandsUI:
    def render_start_screen(self, user_name: str) -> ViewResultDTO:
        # Combines texts.START_GREETING + keyboards.build_start_keyboard()
```

No side effects, no API calls. Easy to test.
