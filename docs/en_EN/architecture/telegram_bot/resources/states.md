# 📜 States

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This module defines FSM (Finite State Machine) states and related configurations for the Telegram Bot. It primarily manages states where incoming text messages from users should be treated as "garbage" and potentially ignored or deleted.

## `GARBAGE_TEXT_STATES`

```python
GARBAGE_TEXT_STATES: list[str] = []
```
A list of strings, where each string represents an FSM state. When the bot is in any of these states, incoming text messages from the user are considered "garbage" and are typically handled by a garbage collector mechanism (e.g., `GarbageStateRegistry` from `core/garbage_collector.py`) to prevent unintended interactions or to clean up the chat.

This list is intended to be populated dynamically or through feature configurations to define contexts where only specific types of input (e.g., button presses, commands) are expected.
