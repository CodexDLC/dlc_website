# 🐍 Django Backend

## Structure

```
src/backend-django/
├── manage.py               # Django management
├── .env                    # Environment variables (dev defaults)
├── .env.example            # Template for .env
├── core/                   # Project config (not an app)
│   ├── settings/
│   │   ├── base.py         # Common settings (reads from .env)
│   │   ├── dev.py          # Development (SQLite, DEBUG=True)
│   │   └── prod.py         # Production (Postgres, HTTPS)
│   ├── urls.py             # Root URL config
│   ├── asgi.py
│   └── wsgi.py
├── features/               # Apps live here (not in root)
│   ├── main/               # Pages, views, static pages
│   │   ├── views/          # Views as folder (one file per view)
│   │   ├── selectors/      # Read queries (DB → view)
│   │   ├── models.py       # Or models/ folder for multiple
│   │   └── urls.py
│   └── system/             # Service models (tags, mixins)
│       ├── models/
│       │   └── mixins.py   # TimestampMixin, etc.
│       └── migrations/
├── static/                 # CSS, JS, images
│   ├── css/
│   ├── js/
│   └── img/
├── templates/              # Django templates
│   ├── base.html
│   └── home/
│       └── home.html
└── locale/                 # i18n translations
```

## Quick Start

```bash
cd src/backend_django
pip install -e "../../.[django,dev]"
python manage.py migrate
python manage.py runserver
```

## Adding a Feature

1. Create app:
```bash
python manage.py startapp my_feature features/my_feature
```

2. Restructure:
   - Move `views.py` → `views/__init__.py` + `views/my_view.py`
   - Add `selectors/` folder for read queries
   - Add `models/` folder if multiple models
   - Update `apps.py`: `name = "features.my_feature"`
   - Add to `core/settings/base.py` → `INSTALLED_APPS`
   - Include URLs in `core/urls.py`

## Architecture Patterns

- **features/** — apps grouped in one place (not scattered in root)
- **views/** as folder — one file per view, not one giant views.py
- **models/** as folder — one file per model when app grows
- **selectors/** — read-only DB queries (keeps views thin)
- **services/** — write operations, business logic (add when needed)
- **split settings** — base/dev/prod, secrets from .env

## Settings

| Variable | Dev Default | Description |
|:---------|:-----------|:------------|
| `SECRET_KEY` | insecure | Django secret key |
| `DEBUG` | True | Debug mode |
| `ALLOWED_HOSTS` | localhost | Comma-separated hosts |
| `DB_NAME` | SQLite | Postgres in production |
| `DB_USER` | — | Postgres user |
| `DB_PASSWORD` | — | Postgres password |
| `DB_HOST` | postgres | Postgres host |
| `LANGUAGE_CODE` | en-us | Default language |
| `TIME_ZONE` | UTC | Timezone |
