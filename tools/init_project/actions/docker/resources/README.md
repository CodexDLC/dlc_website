# docker/resources/

Шаблоны для генерации Docker-инфраструктуры. Читаются `DockerAction` из `docker.py`.

## Структура

```
resources/
├── env.tpl                        # .env (продакшн)
├── env.example.tpl                # .env.example
├── dockerignore.tpl               # .dockerignore
│
├── compose/
│   ├── docker-compose.dev.tpl     # Скелет dev compose (сервисы вставляются кодом)
│   └── docker-compose.prod.tpl    # Скелет prod compose
│
├── fastapi/
│   └── Dockerfile.tpl             # FastAPI backend
│
├── django/
│   ├── Dockerfile.tpl             # Django backend (multi-stage, Poetry)
│   └── entrypoint.sh.tpl          # migrate + collectstatic + gunicorn
│
├── bot/
│   └── Dockerfile.tpl             # Telegram Bot (aiogram)
│
├── worker/
│   └── Dockerfile.tpl             # ARQ worker (src/workers/)
│
├── nginx/
│   ├── Dockerfile.tpl             # Prod: envsubst → site.conf.template при старте
│   ├── nginx-main.conf.tpl        # events + http + JSON logging + rate limits
│   ├── site.conf.tpl              # Prod HTTPS: default_server, SSL, static, proxy
│   └── site-local.conf.tpl        # Dev HTTP: localhost, static, proxy
│
└── github/
    ├── ci-develop.yml.tpl         # Push → develop: lint + mypy (Poetry + cache)
    ├── ci-main.yml.tpl            # PR → main: lint + mypy + pytest + docker build
    ├── cd-release.yml.tpl         # Push tag v*: build + push GHCR + deploy VPS
    └── check-release-source.yml   # Проверка что release создан из main
```

## Маркеры подстановки

| Маркер | Значение |
|--------|---------|
| `{{PROJECT_NAME}}` | имя проекта (из CLI) |
| `{{PYTHON_VERSION}}` | версия Python (сейчас `3.13`) |
| `{{DOMAIN}}` | домен по умолчанию (`project-name.dev`) |
| `{{BUILD_CHECK_STEPS}}` | docker build шаги для `ci-main` (генерируется кодом) |
| `{{BUILD_PUSH_STEPS}}` | docker build+push шаги для `cd-release` |
| `{{DOCKER_IMAGE_ENVS}}` | env блок с именами образов для `cd-release` |
| `{{DOCKER_IMAGE_ENV_NAMES}}` | список имён для `envs:` в SSH шаге |
| `{{UPDATE_VAR_CALLS}}` | `update_var` вызовы для `.env` на VPS |

## Логика Nginx

`site.conf.tpl` генерирует **`deploy/nginx/site.conf.template`** (не `site.conf`).

При старте контейнера `Dockerfile.tpl` выполняет:
```sh
envsubst '${DOMAIN_NAME}' < /etc/templates/site.conf.template > /etc/nginx/conf.d/site.conf
```
Домен задаётся через `DOMAIN_NAME` переменную окружения в `docker-compose.prod.yml`.

## Как добавить новый сервис

1. Создать `resources/myservice/Dockerfile.tpl` с маркером `{{PYTHON_VERSION}}`
2. Добавить в `docker.py` → `execute()`: рендеринг Dockerfile
3. Добавить `_svc_myservice_dev()` и `_svc_myservice_prod()` методы
4. Добавить вызовы в `_generate_compose_dev()` / `_generate_compose_prod()`
5. Добавить `_add_image(...)` вызов в `_generate_workflows()` для CI/CD
