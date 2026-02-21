# tools/dev/

Инструменты разработки: проверка качества кода и генерация документации.

## check.py

Главный quality gate проекта. Запускается перед каждым push.

```bash
python tools/dev/check.py           # полная проверка
python tools/dev/check.py --settings  # интерактивное меню
```

**Что проверяет:**

| Шаг | Инструмент | Что делает |
|-----|-----------|-----------|
| 1. Lint | pre-commit + ruff | trailing whitespace, yaml, форматирование, импорты |
| 2. Types | mypy | полная проверка типов (с очисткой кеша) |
| 3. Tests | pytest | юнит-тесты (`-m unit`) |
| 4. Docker | docker-compose | сборка образов, запуск стека, Django checks, проверка миграций |

**Интерактивное меню** (`--settings`):
```
1. Fast Check (Lint only)
2. Type Check (Mypy)
3. Run Unit Tests
4. Full Docker Validation
5. Run Everything
```

Docker-валидация запускается с изолированным project name (`-p`) чтобы не конфликтовать с dev-стеком. Автоматически чистит контейнеры и volumes после завершения.

---

## generate_project_tree.py

Генерирует визуальное дерево структуры проекта в файл `project_structure.txt`.

```bash
python tools/dev/generate_project_tree.py
```

Предложит выбрать: весь проект или конкретную папку (src/, tools/, deploy/ и т.д.).
Игнорирует `.git`, `__pycache__`, `.venv`, `.pyc` и бинарники.
