# 📜 View DTO

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines several Data Transfer Objects (DTOs) used for structuring and passing UI-related data throughout the Telegram bot application. These DTOs ensure consistent communication between different layers, especially between orchestrators, UI services, and message sending mechanisms.

## `ViewResultDTO`

```python
class ViewResultDTO(BaseModel):
    text: str
    kb: InlineKeyboardMarkup | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
```
A DTO representing a single message to be sent to Telegram, comprising its text content and an optional inline keyboard.

*   `text` (`str`): The text content of the message.
*   `kb` (`InlineKeyboardMarkup | None`): An optional `InlineKeyboardMarkup` object for interactive buttons.
*   `model_config`: Configures Pydantic to allow arbitrary types, specifically for `InlineKeyboardMarkup`.

## `MessageCoordsDTO`

```python
class MessageCoordsDTO(BaseModel):
    chat_id: int
    message_id: int
```
A DTO representing the coordinates (chat ID and message ID) of a specific message in Telegram. This is useful for editing or deleting messages.

*   `chat_id` (`int`): The ID of the chat where the message is located.
*   `message_id` (`int`): The ID of the message itself.

## `UnifiedViewDTO`

```python
class UnifiedViewDTO(BaseModel):
    content: ViewResultDTO | None = None
    menu: ViewResultDTO | None = None
    clean_history: bool = False
    alert_text: str | None = None
    chat_id: int | str | None = None
    session_key: int | str | None = None
    mode: str | None = None
    message_thread_id: int | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
```
A comprehensive DTO representing the full response from an orchestrator. It can contain data for multiple messages (content and menu), control flags, and routing information.

*   `content` (`ViewResultDTO | None`): The main content message to be sent or edited.
*   `menu` (`ViewResultDTO | None`): An optional menu message, typically a persistent dashboard.
*   `clean_history` (`bool`): If `True`, indicates that previous messages in the chat should be deleted.
*   `alert_text` (`str | None`): Text for a Telegram alert (e.g., `answer_callback_query`).
*   `chat_id` (`int | str | None`): The ID of the target chat or channel.
*   `session_key` (`int | str | None`): A key for the session in Redis (e.g., `user_id` or `session_id`).
*   `mode` (`str | None`): Specifies the routing mode (e.g., `"channel"`, `"topic"`, or `None` for private chats).
*   `message_thread_id` (`int | None`): The ID of the message thread (topic) for `mode="topic"`.
*   `model_config`: Configures Pydantic to allow arbitrary types.

## `MenuViewDTO`

```python
class MenuViewDTO(BaseModel):
    text: str
    keyboard: InlineKeyboardMarkup | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
```
A universal DTO for passing ready-to-use UI (text + keyboard) from the service layer to handlers. This is similar to `ViewResultDTO` but might be used in slightly different contexts within the application flow.

*   `text` (`str`): The text content of the menu view.
*   `keyboard` (`InlineKeyboardMarkup | None`): An optional `InlineKeyboardMarkup` for the menu.
*   `model_config`: Configures Pydantic to allow arbitrary types.
