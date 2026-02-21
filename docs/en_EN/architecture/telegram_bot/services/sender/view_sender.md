# 📜 View Sender

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `ViewSender` class, a core service responsible for sending and editing messages in Telegram. It intelligently manages the bot's UI by leveraging Redis to store and retrieve message coordinates (IDs), enabling seamless updates to the user interface.

## `ViewSender` Class

The `ViewSender` acts as a "postman" service, ensuring that the bot's responses are delivered efficiently and that the UI remains consistent, especially when dealing with persistent elements like menus and content messages.

### Initialization (`__init__`)

```python
def __init__(
    self,
    bot: Bot,
    sender_manager: SenderManager,
):
```
Initializes the `ViewSender` service.

*   `bot` (`Bot`): An instance of the `aiogram.Bot` client, used for interacting with the Telegram API.
*   `sender_manager` (`SenderManager`): An instance of `SenderManager` (from `infrastructure/redis/managers/sender`) responsible for managing UI coordinates in Redis.

**Key Actions:**
*   Stores the `bot` and `manager` instances.
*   Initializes internal state variables (`key`, `chat_id`, `is_channel`, `message_thread_id`) to `None` or default values.

### `send` Method

```python
async def send(self, view: UnifiedViewDTO):
```
The main method for synchronizing the bot's UI. It processes a `UnifiedViewDTO` to send or edit messages.

*   `view` (`UnifiedViewDTO`): A DTO containing all necessary information for UI updates, including content, menu, routing details, and control flags.

**Process:**
1.  **Validation:** Checks if `session_key` and `chat_id` are present in the `UnifiedViewDTO`.
2.  **Internal State Update:** Updates the `ViewSender`'s internal `key`, `chat_id`, `message_thread_id`, and `is_channel` based on the `view` DTO.
3.  **Retrieve UI Coordinates:** Fetches existing UI coordinates (message IDs) from Redis using `self.manager.get_coords()`.
4.  **Clean History:** If `view.clean_history` is `True`, it calls `_delete_previous_interface()` to remove old messages and clears coordinates from Redis.
5.  **Process Menu Message:** Calls `_process_message()` for `view.menu` to either edit an existing menu message or send a new one.
6.  **Process Content Message:** Calls `_process_message()` for `view.content` to either edit an existing content message or send a new one.
7.  **Update Redis Coordinates:** If any messages were sent or edited, it updates the corresponding `menu_msg_id` and `content_msg_id` in Redis using `self.manager.update_coords()`.

### `_delete_previous_interface` Method (Private)

```python
async def _delete_previous_interface(self, ui_coords: dict):
```
Asynchronously attempts to delete previously sent menu and content messages based on their IDs stored in `ui_coords`.

*   `ui_coords` (`dict`): A dictionary containing `menu_msg_id` and `content_msg_id`.

**Process:**
*   Uses `self.bot.delete_message()` for both menu and content messages.
*   `contextlib.suppress(TelegramAPIError)` is used to gracefully handle cases where messages might have already been deleted or are inaccessible.

### `_process_message` Method (Private)

```python
async def _process_message(
    self, view_dto: ViewResultDTO | None, old_message_id: int | None, log_prefix: str
) -> int | None:
```
A private helper method to either edit an existing message or send a new one based on the `ViewResultDTO`.

*   `view_dto` (`ViewResultDTO | None`): The DTO containing the text and keyboard for the message.
*   `old_message_id` (`int | None`): The ID of an existing message to edit.
*   `log_prefix` (`str`): A prefix for logging messages (e.g., "MENU", "CONTENT").

**Process:**
1.  **Edit Existing Message:** If `old_message_id` is provided, it attempts to edit the message using `self.bot.edit_message_text()`. If successful, it returns `old_message_id`.
2.  **Send New Message:** If `old_message_id` is `None` (or editing failed), it attempts to send a new message using `self.bot.send_message()`.
3.  **Error Handling:** Catches `TelegramAPIError` during sending and logs the error.

**Returns:**
`int | None`: The `message_id` of the edited or newly sent message, or `None` if an error occurred.
