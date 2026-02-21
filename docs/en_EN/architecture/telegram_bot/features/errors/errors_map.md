# 📜 Errors Map

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Registry of error configurations for the error display system.

**File:** `src/telegram_bot/features/errors/resources/errors_map.py`

---

## 📋 Structure

```python
DEFAULT_ERRORS: dict[str, dict] = {
    "error_code": {
        "title": "Display Title",
        "text": "User-facing description",
        "show_refresh": True,   # Show "Retry" button
        "show_back": True,      # Show "Back" button
    },
}
```

---

## 🔧 Extending

To add custom error screens, add entries to `DEFAULT_ERRORS` or create a feature-specific errors map and merge it in the orchestrator.

---

## 🔗 Usage

```python
# Navigate to error screen from any orchestrator:
await self.director.set_scene("errors", "network")

# Or with a custom exception:
class AppError(Exception):
    code = "custom_error"

await self.director.set_scene("errors", error.code)
```
