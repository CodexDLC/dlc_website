# 📜 Common FSM Handlers

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines common FSM (Finite State Machine) handlers, primarily focusing on a "garbage collector" mechanism. This mechanism is designed to automatically delete unwanted text messages in specific FSM states where only inline button presses or other non-textual input is expected.

## `router`

```python
router = Router(name="common_fsm_router")
```
An instance of `aiogram.Router` specifically for common FSM-related handlers. This router is included in the main application router to ensure these handlers are active across the bot.

## `delete_garbage_text` Handler

```python
@router.message(F.text, IsGarbageStateFilter())
async def delete_garbage_text(m: Message, state: FSMContext):
```
This asynchronous handler is triggered for any incoming text message (`F.text`) when the bot is in a state that has been registered as a "garbage state" by the `IsGarbageStateFilter`.

*   `m` (`Message`): The incoming `Message` object.
*   `state` (`FSMContext`): The FSM context for the current user.

**Purpose:**
To automatically delete text messages that are considered irrelevant or "noise" in specific conversational contexts. This helps maintain a cleaner chat interface and guides the user towards expected interactions (e.g., pressing inline buttons).

**Process:**
1.  **Log Trigger:** Logs an informational message indicating that the garbage collector has been triggered for the user and their current state.
2.  **Attempt Deletion:** Tries to delete the incoming text message using `m.delete()`.
3.  **Log Success/Failure:** Logs a debug message if the deletion is successful, or a warning if `TelegramAPIError` occurs (e.g., the bot does not have permission to delete messages).

**Filter (`IsGarbageStateFilter`):**
This handler uses `IsGarbageStateFilter` to dynamically determine if the current FSM state is one where text messages should be deleted. States are registered as garbage states via the `GarbageStateRegistry` (defined in `core/garbage_collector.py`).
