# 🧩 Database Mixins

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

Mixins allow reusing common fields across different models, following the DRY (Don't Repeat Yourself) principle.

## `TimestampMixin`

**File:** `src/backend-fastapi/database/models/base.py`

Adds automatic tracking of record creation and update times.

### Fields

*   **`created_at`** (`DateTime`): Creation date. Automatically filled by DB (`server_default=func.now()`).
*   **`updated_at`** (`DateTime`): Last modification date. Automatically updated by DB on any UPDATE (`onupdate=func.now()`).

### Usage Example

```python
from app.database.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    # ... other fields ...
    # created_at and updated_at will be added automatically
```
