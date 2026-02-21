# Инструменты

> [Инфраструктура](../README.md) / Инструменты

Утилиты разработки, поставляемые с шаблоном. Директория `tools/` **не удаляется** после установки.

> Подробная документация: [English version](../../../en_EN/infrastructure/tools/README.md)

## Обзор

| Инструмент | Путь | Запуск |
|:-----------|:-----|:-------|
| **Инсталлятор** | `tools/init_project/` | `python -m tools.init_project` |
| **Добавить модуль** | `add_module.py` | `python -m tools.init_project.add_module bot` |
| **Удалить модуль** | `remove_module.py` | `python -m tools.init_project.remove_module bot` |
| **Конвертер изображений** | `tools/media/convert_to_webp.py` | `python tools/media/convert_to_webp.py` |
| **QR генератор** | `tools/media/qr_generator.py` | `python tools/media/qr_generator.py` |
| **Агент миграции** | `tools/migration_agent.py` | `python tools/migration_agent.py /path` |

## Инсталлятор

Модульный инсталлятор: выбор бэкенда (Django/FastAPI), бота, настройка Docker и CI/CD. Два git-коммита: Install (полный снимок) → Activate (чистый проект).

→ [Подробнее (EN)](../../../en_EN/infrastructure/tools/init_project.md)

## Media Tools

- **convert_to_webp.py** — 5 режимов: convert, optimize, resize, restore, info. Оригиналы в `_source/`, откат через restore.
- **qr_generator.py** — GUI (Tkinter) для стилизованных QR-кодов. Экспорт singleton-класса `qr_style.py` с зафиксированным стилем проекта.

→ [Подробнее (EN)](../../../en_EN/infrastructure/tools/media.md)

## Управление модулями

- **add_module** — восстановление модуля из Install-коммита через `git checkout`
- **remove_module** — удаление модуля (src + deploy + docs) + автокоммит

→ [Подробнее (EN)](../../../en_EN/infrastructure/tools/add_remove_module.md)

## Агент миграции

Переносит существующий проект в структуру шаблона: анализ, создание директорий, TODO-отчёт.

→ [Подробнее (EN)](../../../en_EN/infrastructure/tools/migration_agent.md)
