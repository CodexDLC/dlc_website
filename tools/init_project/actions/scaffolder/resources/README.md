# Scaffolder Action — Resources

Здесь будут шаблоны для генерации структур проекта.

## Планируемые ресурсы

```
resources/
├── django/
│   ├── settings.py.tpl         # Django settings с INSTALLED_FEATURES
│   ├── urls.py.tpl             # URLs с auto-discovery features
│   ├── wsgi.py.tpl             # WSGI entry point
│   ├── asgi.py.tpl             # ASGI entry point
│   └── feature/                # Шаблон одной Django feature
│       ├── __init__.py.tpl
│       ├── models.py.tpl
│       ├── views.py.tpl
│       ├── serializers.py.tpl
│       ├── urls.py.tpl
│       └── tests/
│           └── __init__.py.tpl
└── ...
```

## Логика

Scaffolder читает шаблоны, подставляет переменные (имя проекта, имя feature),
и создаёт готовые файлы в `src/`. Используется DjangoInstaller-ом
для полной настройки Django-проекта с feature-based архитектурой.
