# 📜 UI

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../README.md)

This module defines the `ErrorUI` class, which is responsible for rendering error messages and generating corresponding user interface elements, such as inline keyboards.

## `ErrorUI` Class

The `ErrorUI` class provides methods to construct a `ViewResultDTO` based on an error configuration, allowing for dynamic display of error messages to the user.

### `render_error` Method

```python
def render_error(self, error_config: dict) -> ViewResultDTO:
```
Renders an error message and an inline keyboard based on the provided `error_config`.

*   `error_config` (dict): A dictionary containing configuration for the error message, which may include:
    *   `"title"` (str): The title of the error (default: "Error").
    *   `"text"` (str): The main body of the error message (default: "Unknown error").
    *   `"button_text"` (str): The text for the inline button (default: "OK").
    *   `"action"` (str): The callback data for the inline button (default: "refresh"). This can be a simple callback or a navigation command (e.g., "nav:home").

**Process:**
1.  Extracts `title`, `text`, `button_text`, and `action` from the `error_config`, using default values if not provided.
2.  Constructs the full message text by formatting the title and text.
3.  Creates an `InlineKeyboardBuilder` and adds a button with the specified `button_text` and `action` as `callback_data`.
4.  Returns a `ViewResultDTO` containing the formatted text and the generated inline keyboard markup.

**Returns:**
A `ViewResultDTO` object ready to be sent to the user.
