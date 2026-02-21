# 📜 Base

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

This module defines the base classes and conventions for SQLAlchemy models used in the Telegram Bot's direct database mode. It ensures consistent naming conventions for Alembic migrations and provides a mixin for common timestamp fields.

## Naming Convention (`convention`)

```python
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```
This dictionary defines a naming convention for database objects (indexes, unique constraints, check constraints, foreign keys, primary keys). This convention is crucial for generating consistent and predictable names in Alembic database migrations, simplifying schema management.

## `Base` Class

```python
class Base(DeclarativeBase):
    """Base class for all Bot SQLAlchemy models."""
    metadata = MetaData(naming_convention=convention)
```
This is the declarative base class for all SQLAlchemy models in the bot application. All models should inherit from this `Base` class.

*   `metadata`: An instance of `MetaData` configured with the `convention` dictionary, ensuring that all models inheriting from `Base` adhere to the defined naming conventions.

## `TimestampMixin`

```python
class TimestampMixin:
    """Mixin to add created_at and updated_at columns."""
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)
```
A mixin class that provides `created_at` and `updated_at` columns to any SQLAlchemy model it is included in.

*   `created_at`: A `datetime` column that automatically records the creation timestamp of a record. It defaults to the current time on the server.
*   `updated_at`: A `datetime` column that automatically updates to the current time on the server whenever the record is modified.
