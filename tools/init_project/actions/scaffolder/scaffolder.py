"""
Scaffolder Action — ЗАГЛУШКА.

Создание директорий и файлов из шаблонов.

TODO (для Django Installer):
  - Создание feature-структуры (вместо стандартных Django apps)
  - Генерация settings.py с INSTALLED_FEATURES auto-discovery
  - Генерация urls.py с auto-discovery
  - Базовые features (users, etc.)

Шаблоны будут лежать в resources/ рядом:
  actions/scaffolder/resources/
    ├── django/
    │   ├── settings.py.tpl
    │   ├── urls.py.tpl
    │   ├── wsgi.py.tpl
    │   └── feature/           # шаблон одной feature
    │       ├── __init__.py.tpl
    │       ├── models.py.tpl
    │       ├── views.py.tpl
    │       └── ...
    └── ...
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.init_project.config import InstallContext


class ScaffolderAction:
    """Создание структур из шаблонов. Пока заглушка."""

    def execute(self, ctx: InstallContext) -> None:
        print("    ⏭️  Scaffolder action — skipped (not yet implemented)")
