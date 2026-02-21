# 📜 WSGI Configuration (`wsgi.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `wsgi.py` file provides the Web Server Gateway Interface (WSGI) configuration for the Django backend application. It serves as the entry point for WSGI-compatible web servers (like Gunicorn or uWSGI) to communicate with the Django application.

## Purpose

The `wsgi.py` file is essential for deploying Django applications in production environments. It exposes the Django application object that web servers use to handle incoming HTTP requests.

## Script Breakdown

```python
"""
WSGI config for lily_website.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")

application = get_wsgi_application()
```

### `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.dev")`

This line sets the `DJANGO_SETTINGS_MODULE` environment variable to `core.settings.dev`. This tells Django which settings file to use. In a production deployment, this environment variable is typically overridden by the web server (e.g., Gunicorn) to point to `core.settings.prod`.

### `application = get_wsgi_application()`

This line retrieves the WSGI application object from Django. This `application` object is what the WSGI web server uses to serve the Django project.

## Usage

In a production environment, a WSGI server (e.g., Gunicorn) would be configured to run this `wsgi.py` file. For example, a Gunicorn command might look like:

```bash
gunicorn core.wsgi:application --bind 0.0.0.0:8000
```
This command tells Gunicorn to serve the `application` object found in `core.wsgi` on port 8000.
