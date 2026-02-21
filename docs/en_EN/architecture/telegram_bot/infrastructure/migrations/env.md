# 📜 env.py

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module is the core environment configuration file for Alembic migrations in the Telegram Bot's direct database mode. It sets up how Alembic connects to the database, discovers models, and executes migrations, supporting both offline and online (asynchronous) modes.

## Key Components

### Settings

```python
settings = BotSettings()
```
An instance of `BotSettings` is loaded to retrieve database connection details (`DATABASE_URL`, `DB_SCHEMA`) and other relevant configurations.

### Alembic Configuration (`config`)

```python
config = context.config
```
The main Alembic configuration object, which is populated from `alembic.ini`.

### Database URL

```python
if settings.DATABASE_URL:
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```
The `sqlalchemy.url` option in Alembic's configuration is dynamically set using the `DATABASE_URL` from `BotSettings`.

### Target Metadata

```python
try:
    from src.telegram_bot.infrastructure.models.base import Base
    target_metadata = Base.metadata
except ImportError:
    target_metadata = MetaData()
```
Alembic needs to know about all SQLAlchemy models to generate migrations. This section attempts to import `Base.metadata` from `src.telegram_bot.infrastructure.models.base`, which contains the metadata for all declared models. If `Base` is not found (e.g., in a fresh project setup), it defaults to an empty `MetaData`.

### Schema Isolation (`DB_SCHEMA`)

```python
DB_SCHEMA = settings.DB_SCHEMA
```
The database schema name (e.g., "bot_app") is retrieved from `BotSettings` to ensure that migrations are applied within the correct schema, providing isolation.

## Migration Execution Modes

### `run_migrations_offline()`

```python
def run_migrations_offline() -> None:
```
Executes migrations in "offline" mode. In this mode, Alembic does not connect to the database directly. Instead, it generates SQL scripts that can be applied manually. This is useful for environments where direct database access is restricted.

### `do_run_migrations(connection: Connection)`

```python
def do_run_migrations(connection: Connection) -> None:
```
A helper function that configures and runs migrations within a given database connection. This is used by both offline and online modes.

### `run_async_migrations()`

```python
async def run_async_migrations() -> None:
```
Executes migrations in "online" (asynchronous) mode. This mode connects to the database and applies migrations directly. It uses `async_engine_from_config` for asynchronous database interaction.

### `run_migrations_online()`

```python
def run_migrations_online() -> None:
```
A synchronous wrapper for `run_async_migrations()`, allowing the online migration process to be called from synchronous contexts.

## Execution Flow

```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```
Alembic determines whether to run in offline or online mode based on its configuration and then calls the appropriate migration function.
