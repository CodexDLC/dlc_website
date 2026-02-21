# 📜 Common FSM Handlers

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Catch-all router that handles garbage text messages.

**File:** `src/telegram_bot/services/fsm/common_fsm_handlers.py`

---

## 🎯 Purpose

When the bot is showing an inline-keyboard screen and the user types text, that text is unwanted. This handler catches it and deletes it silently.

---

## ⚙️ How It Works

```python
router = Router(name="common_fsm_router")

@router.message(F.text, IsGarbageStateFilter())
async def delete_garbage_text(message: Message):
    await message.delete()
```

- **`F.text`** — Only text messages (not photos, stickers, etc.)
- **`IsGarbageStateFilter()`** — Only in states registered with `GarbageStateRegistry`

---

## 📍 Router Order

This router is always registered **last** by `routers.py`:

```python
def build_main_router():
    main_router = Router()
    for feature_router in collect_feature_routers():
        main_router.include_router(feature_router)
    main_router.include_router(common_fsm_router)  # Last!
    return main_router
```

This ensures feature handlers get priority. The garbage handler only catches messages that nothing else handles.
