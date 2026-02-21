# tools/

Вспомогательные инструменты проекта. Не попадают в продакшн-образы.

```
tools/
├── init_project/       # Инсталлятор — инициализация нового проекта из шаблона
├── dev/                # Инструменты разработки: проверка качества, дерево проекта
├── static/             # Сборка CSS (компиляция @import, минификация)
├── media/              # Работа с медиафайлами: WebP конвертер, QR-генератор
└── migration_agent.py  # Внедрение шаблона в существующий проект
```

## Быстрый старт

```bash
# Инициализировать новый проект из шаблона
python -m tools.init_project

# Проверка качества кода (lint + types + tests + docker)
python tools/dev/check.py

# Интерактивное меню проверок
python tools/dev/check.py --settings

# Собрать CSS (base.css → app.css)
python tools/static/css_compiler.py

# Конвертировать PNG/JPG в WebP
python tools/media/convert_to_webp.py src/backend_django/static/img

# GUI для генерации QR-кодов
python tools/media/qr_generator.py

# Сгенерировать дерево структуры проекта
python tools/dev/generate_project_tree.py

# Перенести шаблон в существующий проект
python tools/migration_agent.py
```
