# 📜 Constants

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This module defines global constants and "magic strings" used throughout the Telegram bot application, primarily for keys used in the FSM (Finite State Machine) context.

## `KEY_UI_COORDS`

```python
KEY_UI_COORDS = "ui_coords"
```
A string constant representing the key used to store UI coordinates (e.g., message IDs for the main menu and content messages) within the FSM context in Redis. This allows the bot to keep track of and manipulate specific messages in the user's chat.
