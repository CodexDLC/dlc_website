---
name: dlc-deployment-architecture
description: Архитектура Docker, Compose и CI/CD DLC Montage. Использовать при создании или изменении deploy-файлов, runtime-образов, инфраструктуры, GitHub Actions и production-развёртывания.
---

# DLC Montage: deploy и CI/CD

## Цель

Каждый исполняемый контур собирается и развёртывается независимо. Каталог `deploy/` владеет упаковкой и соединением сервисов, но не содержит бизнес-логику приложения.

Эталон подхода — `C:\install\projects\pets\TurnBasedMMORPG`: переносить разделение слоёв, проверки и ручные gates, но не игровые имена, сервисы и настройки.

## Владение runtime-образами

Каждый существующий runtime получает собственный каталог и Dockerfile:

```text
deploy/
├── django/Dockerfile
├── telegram/Dockerfile
├── worker/Dockerfile
├── nginx/Dockerfile
├── compose.infra.yml
├── compose.django.yml
├── compose.telegram.yml
├── compose.workers.yml
├── compose.local.yml
└── compose.prod.yml
```

- `django` — HTTP-приложение CRM и будущего сайта.
- `telegram` — Telegram Bot/Mini App adapter; он использует публичные application-сервисы, а не копирует правила отчётов.
- `worker` — ARQ и другие фоновые процессы; бизнес-операции остаются в сервисном слое Django.
- `nginx` — входящий HTTP/TLS-контур, когда он действительно понадобится.
- PostgreSQL и Redis принадлежат `infra` и используют закреплённые официальные образы. Собственный Dockerfile нужен им только при реальной кастомизации.

Не создавать пустые runtime-каталоги заранее. Добавлять Dockerfile одновременно с появлением запускаемого сервиса.

## Compose-слои

- `compose.infra.yml` владеет PostgreSQL, Redis, общей сетью и постоянными volumes; reverse proxy может войти сюда, если остаётся общим входным контуром.
- `compose.django.yml` владеет Django web и одноразовым сервисом миграций.
- `compose.telegram.yml` владеет только Telegram runtime.
- `compose.workers.yml` владеет только workers и scheduler, если он появится.
- `compose.local.yml` и `compose.prod.yml` агрегируют слои через `include` или несколько `-f`; они не дублируют определения сервисов.

Деплой одного слоя не должен перезапускать остальные. Django, Telegram и workers могут использовать общую базу, Redis, lock-файл зависимостей и часть исходников, но не общий mutable runtime-контейнер или неявную локальную файловую систему.

Миграции запускаются отдельным одноразовым сервисом/шагом до обновления Django и зависимых workers. Не выполнять конкурентные `migrate` при старте каждого контейнера.

## Образы и конфигурация

- Сборочный context — корень репозитория; Dockerfile явно копирует только нужные lock-файлы и исходники.
- Использовать multi-stage сборку, непривилегированного runtime-пользователя, healthcheck и минимальный runtime-образ.
- Версии базовых и инфраструктурных образов закреплять; не полагаться на плавающий `latest` как единственный источник production-деплоя.
- Конфигурация поступает через переменные среды или выбранный deploy env-file. Реальные `.env`, ключи, токены и пароли не коммитятся.
- Постоянные данные хранятся только в именованных volumes или внешних сервисах. Загруженные файлы production принадлежат Hetzner S3, а не слою контейнера.
- Local-only порты PostgreSQL, Redis и административных инструментов привязывать к `127.0.0.1`.

## CI/CD

Когда Git-репозиторий и production-контур утверждены, использовать отдельные workflow:

- `ci.yml` — тесты, линтер, миграционные проверки и сборка документации;
- `build-images.yml` — после quality gate независимо собирает существующие runtime-образы;
- `deploy-production.yml` — ручной запуск с выбором слоя `infra`, `django`, `telegram`, `workers` или `full`.

Образы помечаются версией/release tag и полным commit SHA. `latest` допустим только как удобный указатель, но production получает явно выбранный immutable tag. Сбой сборки одного образа не должен приводить к публикации неполного релиза как готового.

Production-деплой, изменение внешней инфраструктуры и отправка образов в registry требуют явного разрешения владельца и утверждённых сервера, домена, registry и secret storage.

## Проверка

Для изменённой поверхности выполнить максимально доступный набор:

```powershell
docker compose -f deploy/compose.<layer>.yml config
docker build -f deploy/<runtime>/Dockerfile .
```

Также проверить healthcheck, одноразовость миграций, отсутствие секретов в Git, immutable image reference и то, что запуск/обновление слоя не затрагивает соседние runtime-контуры.
