# 📜 Sender Key

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../../../README.md)

This module defines the `SenderKeys` class, which provides static methods for generating standardized Redis keys used by the `SenderManager`. These keys are crucial for organizing and accessing UI-related coordinates and message data stored in Redis.

## `SenderKeys` Class

The `SenderKeys` class encapsulates the logic for constructing Redis keys, ensuring consistency across the application.

### `get_user_coords_key` Method

```python
@staticmethod
def get_user_coords_key(user_id: int | str) -> str:
```
Generates a Redis key for storing UI coordinates specific to a particular user in a private chat.

*   `user_id` (`int | str`): The unique identifier of the user.

**Returns:**
`str`: A Redis key in the format `sender:user:{user_id}`.

**Redis Type:** `HASH`
**Example:** `sender:user:123456789`

### `get_channel_coords_key` Method

```python
@staticmethod
def get_channel_coords_key(session_id: str) -> str:
```
Generates a Redis key for storing UI coordinates specific to a channel or group, identified by a session ID.

*   `session_id` (`str`): A unique identifier for the channel or group session.

**Returns:**
`str`: A Redis key in the format `sender:channel:{session_id}`.

**Redis Type:** `HASH`
**Example:** `sender:channel:booking_feed_1`
