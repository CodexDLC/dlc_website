# 💉 Dependencies

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

FastAPI Dependency Injection system documentation.

## Common Dependencies

### `get_db`
Provides a database session (AsyncSession).
- **Scope:** Request
- **Usage:** `db: AsyncSession = Depends(get_db)`

### `get_current_user`
Validates JWT token and returns the current user model.
- **Scope:** Request
- **Usage:** `user: User = Depends(get_current_user)`
- **Raises:** 401 Unauthorized if token is invalid.
