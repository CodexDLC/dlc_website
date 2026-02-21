# 📜 Cache Utilities (`cache.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `cache.py` module provides a universal function for caching data in Django applications. It leverages Django's caching framework (configured to use Redis in `base.py`) to store and retrieve data efficiently, reducing the load on the database and improving response times.

## Purpose

The primary purpose of this module is to offer a simple and consistent way to implement caching logic across the backend, ensuring that frequently accessed data is served from a fast cache rather than being re-fetched or re-computed.

## `get_cached_data()` Function

```python
def get_cached_data(key: str, fetch_func, timeout: int = 60 * 60 * 24):
    """
    Универсальная функция для кэширования данных.
    - key: Уникальный ключ для Redis.
    - fetch_func: Функция, которая вызывается, если данных нет в кэше.
    - timeout: Время жизни кэша (по умолчанию 24 часа).
    """
    data = cache.get(key)

    if data is not None:
        log.debug(f"Cache | action=get status=hit key='{key}'")
        return data

    log.debug(f"Cache | action=get status=miss key='{key}'")

    # Получаем свежие данные
    data = fetch_func()

    # Сохраняем в кэш
    if data is not None:
        # Если это QuerySet, превращаем его в список, чтобы он "застыл" для кэша
        if hasattr(data, "all") and callable(data.all):
            data = list(data)

        cache.set(key, data, timeout)
        log.debug(f"Cache | action=set status=success key='{key}' timeout={timeout}")

    return data
```

### Description

This function attempts to retrieve data from the cache using a given `key`. If the data is not found in the cache (a "cache miss"), it executes a `fetch_func` to get the fresh data, stores it in the cache, and then returns it.

### Arguments

*   `key` (`str`): A unique string identifier used as the key for storing and retrieving data in Redis (or the configured cache backend).
*   `fetch_func`: A callable (function or method) that will be executed to fetch the data if it's not found in the cache. This function should return the data to be cached.
*   `timeout` (`int`): The time-to-live (TTL) for the cached data, in seconds. Defaults to 24 hours (`60 * 60 * 24`).

### Process

1.  **Attempt Cache Retrieval:** Calls `cache.get(key)` to check if the data exists in the cache.
2.  **Cache Hit:** If `data` is found in the cache (`data is not None`), it logs a "cache hit" and returns the cached data immediately.
3.  **Cache Miss:** If `data` is not found, it logs a "cache miss".
4.  **Fetch Fresh Data:** Executes `fetch_func()` to retrieve the data.
5.  **Cache Data:** If the fetched `data` is not `None`:
    *   **QuerySet Handling:** If the `data` is a Django `QuerySet` (detected by `hasattr(data, "all") and callable(data.all)`), it converts the `QuerySet` to a `list`. This "freezes" the `QuerySet`'s results at the time of caching, preventing unexpected behavior if the underlying database changes later.
    *   Calls `cache.set(key, data, timeout)` to store the fetched data in the cache with the specified `timeout`.
    *   Logs a success message for caching.
6.  **Return Data:** Returns the fetched (and potentially cached) data.

## Usage

This function can be used in any part of the Django application where data needs to be cached. For example:

```python
from .cache import get_cached_data
from features.booking.models import Service

def get_all_services():
    return get_cached_data(
        key="all_services",
        fetch_func=lambda: Service.objects.all().order_by('name'),
        timeout=60 * 60 # Cache for 1 hour
    )
```
