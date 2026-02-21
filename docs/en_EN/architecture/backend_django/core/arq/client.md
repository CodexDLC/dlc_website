# 📜 ARQ Client (`client.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `client.py` module provides a client for interacting with the ARQ task queue from within the Django backend. It enables Django views (which are typically synchronous) to enqueue asynchronous tasks to Redis for processing by ARQ workers.

## Purpose

The `DjangoArqClient` acts as a producer, allowing the Django application to offload long-running or non-blocking operations to background workers, thereby improving the responsiveness of the web application.

## `DjangoArqClient` Class

The `DjangoArqClient` is a class-based client that manages a single asynchronous Redis connection pool for ARQ.

### Class Attributes

*   `_pool: ArqRedis | None = None`:
    A class-level attribute to store the `ArqRedis` connection pool. This ensures that only one connection pool is created and reused across all instances of the client.

### `get_pool()` Method

```python
@classmethod
async def get_pool(cls) -> ArqRedis:
    """
    Returns (or creates) an async Redis pool.
    """
    if cls._pool is None:
        redis_settings = RedisSettings(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            database=0,
        )
        cls._pool = await create_pool(redis_settings)
    return cls._pool
```

### Description

This asynchronous class method returns the ARQ Redis connection pool. If the pool does not already exist, it creates one using Redis connection settings from Django's `settings`.

### `enqueue_job_async()` Method

```python
@classmethod
async def enqueue_job_async(cls, function: str, *args: Any, **kwargs: Any) -> Any | None:
    """
    Async method to enqueue a job.
    """
    try:
        pool = await cls.get_pool()
        job = await pool.enqueue_job(function, *args, **kwargs)
        return job
    except Exception as e:
        print(f"ARQ Error: Failed to enqueue job '{function}': {e}")
        return None
```

### Description

This asynchronous class method enqueues a job to the ARQ Redis queue. It retrieves the connection pool and then calls `pool.enqueue_job()`.

### Arguments

*   `function` (`str`): The name of the worker function to be executed by an ARQ worker.
*   `*args` (`Any`): Positional arguments to pass to the worker function.
*   `**kwargs` (`Any`): Keyword arguments to pass to the worker function.

### `enqueue_job()` Method

```python
@classmethod
def enqueue_job(cls, function: str, *args: Any, **kwargs: Any) -> Any | None:
    """
    Synchronous wrapper to enqueue a job from Django views.
    """
    return async_to_to_sync(cls.enqueue_job_async)(function, *args, **kwargs)
```

### Description

This synchronous class method provides a convenient wrapper to enqueue a job from synchronous Django views or other synchronous parts of the application. It uses `asgiref.sync.async_to_sync` to call the asynchronous `enqueue_job_async` method.

### Arguments

*   `function` (`str`): The name of the worker function.
*   `*args` (`Any`): Positional arguments for the worker function.
*   `**kwargs` (`Any`): Keyword arguments for the worker function.

## Usage

To enqueue a task from a Django view:

```python
from core.arq.client import DjangoArqClient

def my_view(request):
    # ... some logic ...
    DjangoArqClient.enqueue_job("my_worker_task", arg1="value1", arg2="value2")
    # ... continue with view logic ...
```
