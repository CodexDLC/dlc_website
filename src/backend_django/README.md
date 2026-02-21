# 🐍 dlc_website — Django Backend

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
cd src/backend-django
pip install -e "../../.[django,dev]"
python manage.py migrate
python manage.py runserver
```

## Adding a Feature

```bash
cd src/backend-django
python manage.py startapp my_feature features/my_feature
```

Then restructure:
1. Move `views.py` → `views/__init__.py` + `views/my_view.py`
2. Add `selectors/` folder
3. Update `apps.py`: `name = "features.my_feature"`
4. Add to `core/settings/base.py` → `INSTALLED_APPS`
5. Include URLs in `core/urls.py`

## Settings

| Variable | Dev Default | Description |
|:---------|:-----------|:------------|
| `SECRET_KEY` | insecure | Django secret key |
| `DEBUG` | True | Debug mode |
| `ALLOWED_HOSTS` | localhost | Comma-separated hosts |
| `DATABASE_URL` | SQLite | Postgres in production |
| `LANGUAGE_CODE` | en-us | Default language |
| `TIME_ZONE` | UTC | Timezone |
