# 📜 Dependencies

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines common dependencies and their initialization/cleanup functions for all ARQ worker modules. It centralizes the setup of shared resources like the Redis client and site settings manager, making them available in the worker's context.

## `init_common_dependencies` Function

```python
async def init_common_dependencies(ctx: dict, settings: WorkerSettings) -> None:
```
An asynchronous function responsible for initializing common dependencies required by ARQ workers. This function is typically called during the worker's startup phase.

*   `ctx` (`dict`): The ARQ worker's context dictionary, where initialized dependencies will be stored.
*   `settings` (`WorkerSettings`): An instance of `WorkerSettings` containing application configurations.

**Process:**
1.  **Redis Client Initialization:** Creates an asynchronous Redis client using `settings.redis_url`, configured to decode responses as UTF-8 strings. The client is stored in `ctx["redis_client"]`.
2.  **Redis Service Initialization:** Initializes a `RedisService` with the created Redis client. The service is stored in `ctx["redis_service"]`.
3.  **Site Settings Manager Initialization:** Initializes a `SiteSettingsManager` with the `RedisService` and `WorkerSettings`.
4.  **Site Settings Loading:** Retrieves the site settings as a Pydantic object using `site_settings_manager.get_settings_obj()` and stores it in `ctx["site_settings"]`.
5.  **Logging:** Logs informational messages about the initialization process.

**Raises:**
`Exception`: If any error occurs during the initialization of dependencies.

## `close_common_dependencies` Function

```python
async def close_common_dependencies(ctx: dict, settings: WorkerSettings) -> None:
```
An asynchronous function responsible for cleaning up common resources initialized by `init_common_dependencies`. This function is typically called during the worker's shutdown phase.

*   `ctx` (`dict`): The ARQ worker's context dictionary.
*   `settings` (`WorkerSettings`): An instance of `WorkerSettings` (included for type consistency, though not directly used in this function).

**Process:**
1.  **Redis Client Cleanup:** Retrieves the `redis_client` from the `ctx`. If present, it closes the Redis connection.
2.  **Logging:** Logs informational messages about the cleanup process.
