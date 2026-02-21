# 📜 ASGI Configuration (`asgi.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `asgi.py` file provides the Asynchronous Server Gateway Interface (ASGI) configuration for the Django backend application. It serves as the entry point for ASGI-compatible web servers (like Uvicorn or Daphne) to communicate with the Django application, enabling support for asynchronous operations like WebSockets and long-polling.

## Purpose

The `asgi.py` file is essential for deploying Django applications that require asynchronous capabilities. It exposes the Django application object that ASGI web servers use to handle incoming requests.

## Script Breakdown

```python
"""
ASGI config for lily_website.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")

application = get_asgi_application()
```

### `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")`

This line sets the `DJANGO_SETTINGS_MODULE` environment variable to `core.settings.dev`. This tells Django which settings file to use. In a production deployment, this environment variable is typically overridden by the web server (e.g., Uvicorn) to point to `core.settings.prod`.

### `application = get_asgi_application()`

This line retrieves the ASGI application object from Django. This `application` object is what the ASGI web server uses to serve the Django project.

## Usage

In an environment requiring asynchronous features (e.g., WebSockets), an ASGI server (e.g., Uvicorn) would be configured to run this `asgi.py` file. For example, a Uvicorn command might look like:

```bash
uvicorn core.asgi:application --host 0.0.0.0 --port 8000
```
This command tells Uvicorn to serve the `application` object found in `core.asgi` on port 8000.
