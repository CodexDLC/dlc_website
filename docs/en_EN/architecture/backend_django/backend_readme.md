# 📜 Backend README (`README.md`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `README.md` file, located in `src/backend_django/`, provides a high-level overview of the Django backend project, its structure, quick start instructions, and guidelines for adding new features.

## Structure

The `README` outlines the directory structure of the `src/backend_django/` folder, highlighting key components:

*   `manage.py`: Django's command-line utility.
*   `.env`: Environment variables for local development.
*   `.env.example`: Template for the `.env` file.
*   `core/`: Contains project-wide configurations (settings, URLs, WSGI/ASGI).
*   `features/`: Directory for modular Django applications (features).
*   `static/`: Static files (CSS, JS, images).
*   `templates/`: Django HTML templates.
*   `locale/`: Internationalization files.

## Quick Start

Provides a concise set of commands to get the Django backend running locally:

1.  `cd src/backend_django`: Navigate to the backend directory.
2.  `pip install -e "../../.[django,dev]"`: Install project dependencies using pip, including Django and development-specific packages.
3.  `python manage.py migrate`: Apply database migrations.
4.  `python manage.py runserver`: Start the Django development server.

## Adding a Feature

Outlines the process for adding a new feature (Django app) to the project, emphasizing the modular structure:

1.  Create the app using `python manage.py startapp my_feature features/my_feature`.
2.  Restructure the app's files (e.g., move views to a `views/` subdirectory, add `selectors/`).
3.  Update `apps.py` with the correct app name.
4.  Add the new app to `INSTALLED_APPS` in `core/settings/base.py`.
5.  Include the app's URLs in `core/urls.py`.

## Settings

Provides a table summarizing key environment variables and their default values for development:

*   `SECRET_KEY`: Django's secret key.
*   `DEBUG`: Debug mode status.
*   `ALLOWED_HOSTS`: Allowed hostnames for the application.
*   `DATABASE_URL`: Database connection URL.
*   `LANGUAGE_CODE`: Default language code.
*   `TIME_ZONE`: Default timezone.
