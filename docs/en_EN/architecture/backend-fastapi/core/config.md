# 📜 Config Module

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

**File:** `src/backend-fastapi/core/config.py`

This module handles application configuration loading and validation using `pydantic-settings`.

## Key Features

*   Reads variables from `.env` file.
*   Reads Environment Variables (OS level).
*   Validates data types (e.g., ensures `MAX_UPLOAD_SIZE` is an integer).
*   Automatically computes file paths (e.g., path to logs).

## Usage

```python
from app.core.config import settings

# Get secret key
key = settings.SECRET_KEY

# Get upload directory path
upload_path = settings.UPLOAD_DIR
```

## Key Settings

*   `SECRET_KEY`: Key for JWT signing.
*   `DATABASE_URL`: Database connection string.
*   `DEBUG`: Debug mode flag.
*   `UPLOAD_DIR`: Path to the image storage directory.

## ⚠️ Production Notes (Docker)

### Persistent Directories

The following directories **MUST** be mounted as Docker Volumes, otherwise data will be lost upon container rebuild:

*   `UPLOAD_DIR` (`data/uploads/`) - Physical image files (CAS).
*   `LOG_DIR` (`data/logs/`) - Application logs.
