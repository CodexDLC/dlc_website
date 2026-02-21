"""
Интерактивный CLI опросник.

Собирает выбор пользователя: имя проекта, бэкенд, бот, git.
Возвращает InstallContext.
"""

from pathlib import Path

from tools.init_project.config import InstallContext


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    """Спрашивает y/n, возвращает bool."""
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{prompt} {suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def _ask_backend() -> str | None:
    """Выбор бэкенд-фреймворка."""
    print("Select backend framework:")
    print("  1. FastAPI  — async REST API (ready in template)")
    print("  2. Django   — full-stack framework (will be installed)")
    print("  3. None     — no backend")
    print()

    while True:
        choice = input("Enter number [1]: ").strip()
        if not choice or choice == "1":
            return "fastapi"
        elif choice == "2":
            return "django"
        elif choice == "3":
            return None
        else:
            print("  ❌ Enter 1, 2, or 3.")


def collect_choices(project_root: Path) -> InstallContext | None:
    """Запускает опросник, возвращает InstallContext."""

    # Имя проекта — default из имени папки
    default_name = project_root.name
    project_name = input(f"Project name [{default_name}]: ").strip()
    if not project_name:
        project_name = default_name

    # Валидация имени
    project_name = project_name.lower().replace(" ", "-")
    print()

    # Бэкенд
    backend = _ask_backend()
    print()

    # Telegram Bot
    include_bot = _ask_yes_no("Include Telegram Bot?", default=True)
    print()

    # Хотя бы что-то должно быть выбрано
    if not backend and not include_bot:
        print("  ⚠️  You must select at least a backend or a bot.")
        return None

    # Git
    init_git = _ask_yes_no("Initialize git repository?", default=True)

    return InstallContext(
        project_root=project_root,
        project_name=project_name,
        backend=backend,
        include_bot=include_bot,
        init_git=init_git,
    )
