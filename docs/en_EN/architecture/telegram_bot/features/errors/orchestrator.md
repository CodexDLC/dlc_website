# 📜 Errors Orchestrator

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Displays configurable error screens based on error codes.

**File:** `src/telegram_bot/features/errors/logic/orchestrator.py`

---

## 🏗️ Class: ErrorOrchestrator

```text
BaseBotOrchestrator
  └── ErrorOrchestrator
```

### Constructor

No dependencies. Loads `DEFAULT_ERRORS` map from `resources/errors_map.py`.

---

## 🔄 Entry Flow

```text
handle_entry(user_id, payload)
│
├── 1. Determine error_code from payload:
│       ├── str → use as error code
│       ├── Exception with .code → use .code
│       └── else → "default"
├── 2. Verify error_code exists in errors_map
│       └── Fallback to "default" if not found
└── 3. await self.render(error_code)
        └── render_content(error_code)
            └── self.ui.render_error(error_config)
```

---

## 🗺️ Error Codes

Defined in `resources/errors_map.py` as `DEFAULT_ERRORS` dictionary:

```python
DEFAULT_ERRORS = {
    "default": {"title": "Error", "text": "Something went wrong", ...},
    "network": {"title": "Connection Error", ...},
    "forbidden": {"title": "Access Denied", ...},
}
```

Each entry configures: title, description text, available buttons (refresh, back).

---

## 🔗 Invocation

The errors feature is invoked **programmatically** via Director:

```python
# From any orchestrator:
await self.director.set_scene("errors", "network")
```

It also has its own router for handling refresh/back buttons within the error screen.
