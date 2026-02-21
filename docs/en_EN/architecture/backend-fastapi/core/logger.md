# 📜 Logger Module

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

**File:** `src/backend-fastapi/core/logger.py`

Structured logging configuration using the **Loguru** library.

## Features

*   **Standard Logging Interception:** All logs from libraries (FastAPI, SQLAlchemy) are redirected to Loguru.
*   **Stream Separation:**
    *   `Console`: Colored output for development.
    *   `File (debug.log)`: Full log of all events.
    *   `File (errors.json)`: Error log in JSON format for easy parsing (ELK/Graylog).
*   **Rotation:** Log files are automatically rotated when they reach a certain size (configured in settings).

## Usage

```python
from loguru import logger

logger.info("User logged in", user_id=123)
logger.error("Database connection failed", error=str(e))
```
