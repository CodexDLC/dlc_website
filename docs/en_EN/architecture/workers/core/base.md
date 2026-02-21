# 📜 Base

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This module provides foundational components for ARQ workers, including a wrapper for the ARQ Redis client (`ArqService`), common startup and shutdown hooks (`base_startup`, `base_shutdown`), and a base class for worker settings (`BaseArqSettings`).

## `ArqService` Class

The `ArqService` acts as a convenient wrapper around the `arq` library's Redis client, simplifying the management of Redis connection pools and job enqueuing.

### Initialization (`__init__`)

```python
def __init__(self, redis_settings: RedisSettings):
```
Initializes the `ArqService` with Redis connection settings.

*   `redis_settings` (`RedisSettings`): An instance of `arq.connections.RedisSettings` containing connection details for Redis.

### `init` Method

```python
async def init(self):
```
Asynchronously initializes the ARQ Redis connection pool. This method should be called once during application startup.

### `close` Method

```python
async def close(self):
```
Asynchronously closes the ARQ Redis connection pool. This method should be called during application shutdown to release resources.

### `enqueue_job` Method

```python
async def enqueue_job(self, function: str, *args: Any, **kwargs: Any) -> Any | None:
```
Enqueues a job into the ARQ queue.

*   `function` (`str`): The name of the worker function to be executed.
*   `*args` (`Any`): Positional arguments to pass to the worker function.
*   `**kwargs` (`Any`): Keyword arguments to pass to the worker function.

**Returns:**
`Any | None`: The ARQ job object if successfully enqueued, otherwise `None`.

## `base_startup` Function

```python
async def base_startup(ctx: dict) -> None:
```
An asynchronous function providing basic startup logic for all ARQ workers. It logs an informational message.

## `base_shutdown` Function

```python
async def base_shutdown(ctx: dict) -> None:
```
An asynchronous function providing basic shutdown logic for all ARQ workers. It logs an informational message.

## `BaseArqSettings` Class

This class defines common base settings for all ARQ workers. Worker-specific settings should inherit from this class and override attributes as needed.

### Attributes

*   `max_jobs` (`int`): The maximum number of jobs an ARQ worker can process concurrently (default: `20`).
*   `job_timeout` (`int`): The maximum time (in seconds) a job is allowed to run before being considered failed (default: `60`).
*   `keep_result` (`int`): The time (in seconds) to keep job results in Redis (default: `5`).
*   `on_startup` (`Callable`): Reference to the `base_startup` function, executed when the worker starts.
*   `on_shutdown` (`Callable`): Reference to the `base_shutdown` function, executed when the worker shuts down.
