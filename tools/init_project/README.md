# tools/init_project/

Инсталлятор нового проекта. Превращает шаблон в готовый проект под конкретные нужды.

## Запуск

```bash
python -m tools.init_project
```

Задаёт вопросы и генерирует проект:

```
Project name [my-project]: my-app
Select backend: 1. FastAPI  2. Django  3. None
Include Telegram Bot? [Y/n]:
Initialize git repository? [Y/n]:
```

## Архитектура

```
init_project/
├── __main__.py         # Точка входа
├── cli.py              # Опросник (сбор InstallContext)
├── config.py           # InstallContext, MODULES реестр
├── runner.py           # Оркестратор flow
│
├── actions/            # Атомарные действия
│   ├── cleaner/        # Удаляет ненужные модули (src/, docs/)
│   ├── renamer/        # Заменяет "project-template" → project_name
│   ├── docker/         # Генерирует deploy/ и .github/ из .tpl шаблонов
│   ├── poetry/         # Чистит зависимости pyproject.toml
│   ├── scaffolder/     # Создаёт структуру src/ (для Django)
│   └── finalizer/      # Git коммиты
│
└── installers/         # Установщики модулей
    ├── shared_installer.py    # Общие зависимости (всегда)
    ├── fastapi_installer.py   # FastAPI настройка
    ├── django_installer.py    # Django настройка (+ шаблоны из django/resources/)
    └── bot_installer.py       # Telegram Bot настройка
```

## Flow установки

```
git commit "Install"   ← снимок ВСЕХ файлов шаблона (точка возврата)
  ↓
installers.pre_install  ← подготовка
installers.install      ← установка зависимостей, копирование файлов
  ↓
CleanerAction    ← удаляет src/ модули которые не нужны
RenamerAction    ← заменяет "project-template" во всех файлах
DockerAction     ← генерирует deploy/ и .github/ из .tpl
PoetryAction     ← чистит pyproject.toml от лишних групп
ScaffolderAction ← создаёт структуру src/ (Django feature-based)
  ↓
installers.post_install  ← финальная настройка
  ↓
git commit "Activate"  ← чистый проект без артефактов шаблона
```

## Добавление/удаление модулей после установки

```bash
# Добавить модуль (бот, воркер)
python -m tools.init_project add bot

# Удалить модуль
python -m tools.init_project remove bot
```

## docker/ action — генерация инфраструктуры

`actions/docker/docker.py` читает `.tpl` шаблоны из `actions/docker/resources/`
и генерирует финальные файлы в `deploy/` и `.github/workflows/`.

Что генерируется зависит от выбора пользователя:

| Выбор | Генерируется |
|-------|-------------|
| FastAPI | `deploy/fastapi/Dockerfile`, nginx, compose |
| Django | `deploy/django/Dockerfile` + `entrypoint.sh`, nginx, compose |
| Bot | `deploy/bot/Dockerfile`, `deploy/worker/Dockerfile` |
| Любой бэкенд | `deploy/nginx/` (4 файла), `.github/workflows/` (4 файла) |
