# 📜 Stream Processor

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the `RedisStreamProcessor` class, which is responsible for continuously reading and processing messages from a Redis Stream. It leverages the `StreamManager` for low-level Redis interactions and dispatches processed messages to a registered callback function.

## `RedisStreamProcessor` Class

The `RedisStreamProcessor` implements a polling loop to consume messages from a Redis Stream, ensuring reliable and asynchronous processing of events.

### Initialization (`__init__`)

```python
def __init__(
    self,
    stream_manager: StreamManager,
    stream_name: str,
    consumer_group_name: str,
    consumer_name: str,
    batch_count: int = 10,
    poll_interval: float = 1.0,
):
```
Initializes the `RedisStreamProcessor`.

*   `stream_manager` (`StreamManager`): An instance of `StreamManager` for interacting with Redis Streams.
*   `stream_name` (`str`): The name of the Redis Stream to listen to.
*   `consumer_group_name` (`str`): The name of the consumer group this processor belongs to.
*   `consumer_name` (`str`): The unique name of this consumer within the group.
*   `batch_count` (`int`): The maximum number of messages to read in a single batch (default: `10`).
*   `poll_interval` (`float`): The interval (in seconds) to wait between polling attempts if no new messages are available (default: `1.0`).

**Key Actions:**
*   Initializes internal state variables, including `is_running` (set to `False`) and `_message_callback` (set to `None`).

### `set_message_callback` Method

```python
def set_message_callback(self, callback: Callable[[dict[str, Any]], Awaitable[None]]):
```
Sets the asynchronous callback function that will be invoked for each processed message.

*   `callback` (`Callable[[dict[str, Any]], Awaitable[None]]`): An asynchronous function that accepts a dictionary (the message data) and returns `None`.

### `start_listening` Method

```python
async def start_listening(self):
```
Starts the Redis Stream listening loop.

**Process:**
1.  Checks if the processor is already running to prevent duplicate starts.
2.  Calls `stream_manager.create_group()` to ensure the consumer group exists for the specified stream.
3.  Sets `self.is_running` to `True`.
4.  Creates an asyncio task to run the `_consume_loop()` method in the background.
5.  Logs an informational message indicating that the processor has started.

### `stop_listening` Method

```python
async def stop_listening(self):
```
Stops the Redis Stream listening loop.

**Process:**
1.  Sets `self.is_running` to `False`, which will cause the `_consume_loop()` to exit gracefully.
2.  Logs an informational message indicating that the processor has stopped.

### `_consume_loop` Method (Private)

```python
async def _consume_loop(self):
```
The main asynchronous loop that continuously reads messages from the Redis Stream.

**Process:**
1.  **Loop Condition:** Continues as long as `self.is_running` is `True`.
2.  **Read Messages:** Calls `stream_manager.read_events()` to fetch a batch of messages.
3.  **Poll Interval:** If no messages are received, it pauses for `self.poll_interval` seconds.
4.  **Process Messages:** Iterates through received messages, calling `_process_single_message()` for each.
5.  **Error Handling:** Includes a `try-except` block to catch and log any exceptions that occur within the loop, with a pause before retrying.

### `_process_single_message` Method (Private)

```python
async def _process_single_message(self, message_id: str, data: dict[str, Any]):
```
Processes a single message received from the Redis Stream and acknowledges its processing.

*   `message_id` (`str`): The ID of the message in the Redis Stream.
*   `data` (`dict[str, Any]`): The content of the message.

**Process:**
1.  **Callback Invocation:** If `_message_callback` is set, it invokes the callback with the message `data`.
2.  **Acknowledge Event:** Calls `stream_manager.ack_event()` to acknowledge that the message has been successfully processed, preventing it from being re-delivered.
3.  **Error Handling:** Catches and logs any exceptions that occur during message processing.
