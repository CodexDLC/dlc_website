# 📜 Entrypoint Script (`entrypoint.sh`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

This `entrypoint.sh` script is executed when the backend Docker container starts. It automates essential setup tasks before launching the Gunicorn server for the Django application.

## Purpose

The script ensures that the Django application is properly initialized within the container by:
1.  Collecting static files.
2.  Applying database migrations.
3.  Starting the Gunicorn production server.

## Script Breakdown

```bash
#!/bin/sh
set -e

echo "Running collectstatic..."
python /app/manage.py collectstatic --noinput

echo "Running migrations..."
python /app/manage.py migrate --noinput

echo "Starting gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 90
```

### `#!/bin/sh`

Shebang line, specifying that the script should be executed with `/bin/sh`.

### `set -e`

This command ensures that the script will exit immediately if any command fails. This is crucial for deployment scripts to prevent partial or broken deployments.

### `echo "Running collectstatic..."`

Prints a message to the console indicating that static file collection is starting.

### `python /app/manage.py collectstatic --noinput`

Executes the Django `collectstatic` command.
*   `--noinput`: Prevents the command from prompting the user for input (e.g., confirmation to overwrite files).
This command gathers all static files from Django apps and places them in the `STATIC_ROOT` directory, making them available for Nginx to serve.

### `echo "Running migrations..."`

Prints a message to the console indicating that database migrations are starting.

### `python /app/manage.py migrate --noinput`

Executes the Django `migrate` command.
*   `--noinput`: Prevents the command from prompting the user for input.
This command applies any pending database migrations, ensuring that the database schema is up-to-date with the Django models.

### `echo "Starting gunicorn..."`

Prints a message to the console indicating that the Gunicorn server is starting.

### `exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 90`

Starts the Gunicorn WSGI HTTP server.
*   `exec`: Replaces the current shell process with the Gunicorn process. This is a best practice in Docker containers as it ensures signals (like `SIGTERM`) are correctly passed to the application, allowing for graceful shutdowns.
*   `core.wsgi:application`: Specifies the WSGI application to serve (Django's WSGI application).
*   `--bind 0.0.0.0:8000`: Binds the Gunicorn server to all network interfaces on port 8000.
*   `--workers 2`: Configures Gunicorn to use 2 worker processes.
*   `--timeout 90`: Sets the worker timeout to 90 seconds.
