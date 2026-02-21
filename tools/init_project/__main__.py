"""
Точка входа: python -m tools.init_project

Определяет корень проекта, запускает CLI опросник,
передаёт выбор пользователя в runner.
"""

import sys
from pathlib import Path

# project_root = tools/init_project/../../ → корень репо
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    print()
    print("═" * 45)
    print("  🚀 Project Template Installer")
    print("═" * 45)
    print()

    from tools.init_project.cli import collect_choices
    from tools.init_project.runner import run

    choices = collect_choices(PROJECT_ROOT)

    if choices is None:
        print("\n❌ Installation cancelled.")
        sys.exit(0)

    print()
    print("─" * 45)
    print(f"  Project name:  {choices.project_name}")
    print(f"  Backend:       {choices.backend or 'None'}")
    print(f"  Telegram Bot:  {'Yes' if choices.include_bot else 'No'}")
    print(f"  Git init:      {'Yes' if choices.init_git else 'No'}")
    print("─" * 45)
    print()

    confirm = input("Proceed with installation? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        print("\n❌ Installation cancelled.")
        sys.exit(0)

    run(choices)
    print("\n✅ Project initialized successfully!")


if __name__ == "__main__":
    main()
