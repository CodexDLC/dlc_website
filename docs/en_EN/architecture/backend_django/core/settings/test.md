# 📜 Test Settings (`test.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This `test.py` file contains Django settings specifically configured for running tests. It inherits from `base.py` and overrides certain settings to optimize for test execution speed and isolation, primarily by using an in-memory SQLite database and in-memory caching.

## Purpose

The `test.py` settings aim to:
*   Accelerate test execution by using faster, in-memory alternatives for the database and cache.
*   Ensure test isolation by providing a clean database for each test run.
*   Simplify Redis password handling during tests.
*   Use a local email backend for testing email functionalities without sending actual emails.

## Sections

### Inheritance

```python
from .base import *  # noqa: F403
```
This line imports all settings from `base.py`, making them available in `test.py`. This ensures that common configurations are inherited, and only test-specific settings need to be defined or overridden.

### Debug

*   `DEBUG = True`: Explicitly sets Django's debug mode to `True` for tests. This can be useful for debugging test failures, as it provides more detailed error information.

### Database — SQLite In-Memory

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
```
This section overrides the `DATABASES` setting to use an in-memory SQLite database for the `default` connection.
*   `"NAME": ":memory:"`: Configures SQLite to create the database entirely in RAM, which is significantly faster than disk-based databases and ensures that each test run starts with a fresh, empty database.

### Cache — In-Memory

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}
```
This section overrides the `CACHES` setting to use an in-memory cache backend.
*   `"BACKEND": "django.core.cache.backends.locmem.LocMemCache"`: Uses Django's local memory cache, which is fast and does not require an external Redis server during tests.
*   `"LOCATION": "test-cache"`: A unique identifier for this cache instance.

### Redis Password

*   `REDIS_PASSWORD = None`: Explicitly sets `REDIS_PASSWORD` to `None` for tests. This simplifies test setup by removing the need for a Redis password when using the in-memory cache.

### Email Backend

*   `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"`: Configures Django to use an in-memory email backend. This means that emails sent during tests will not actually be delivered but will be stored in memory, allowing tests to inspect their content.

### Password Hashers (Optional)

```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
```
This setting (if uncommented) configures Django to use a faster, less secure password hasher (MD5) during tests. This can speed up test execution, especially for tests involving user authentication, as password hashing is a CPU-intensive operation. It should *never* be used in production.
