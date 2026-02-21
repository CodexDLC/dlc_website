# 📜 Database Module

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

**File:** `src/backend-fastapi/core/database.py`

This module handles asynchronous connection to the PostgreSQL database using `SQLAlchemy`.

## Components

### `async_engine`

The database engine. Configured with connection pooling (`pool_size=20`) and SSL support.

### `get_db`

FastAPI Dependency. Used to obtain a DB session in request handlers.

**Important:** We use the **Explicit Commit** strategy. This means `get_db` does not automatically commit transactions. The call to `await session.commit()` must occur explicitly in the service layer.

## Data Storage Structure

Models and repositories are separated into the `src/backend-fastapi/database/` layer:

*   **Models (`database/models/`)**: DB Table definitions (SQLAlchemy).
*   **Repositories (`database/repositories/`)**: Database interaction methods.

## Usage

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    # ... work with DB ...
    pass
```
