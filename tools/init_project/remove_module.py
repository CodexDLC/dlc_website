"""
Remove Module — удаление модулей из проекта.

Удаляет все директории модуля (src, deploy, docs) и коммитит:

  python -m tools.init_project.remove_module bot
  python -m tools.init_project.remove_module fastapi
  python -m tools.init_project.remove_module django

Можно восстановить обратно через add_module.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.init_project.config import MODULES, safe_rmtree

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Алиасы (зеркалят add_module)
_ALIASES: dict[str, str] = {
    "bot": "telegram_bot",
}


def _resolve_name(name: str) -> str:
    """Приводит алиас к каноническому имени модуля."""
    return _ALIASES.get(name, name)


def _all_paths(module_key: str) -> list[str]:
    """Собирает все пути модуля: src + deploy + docs."""
    cfg = MODULES[module_key]
    return cfg.src_dirs + cfg.deploy_dirs + cfg.doc_dirs


def _available_names() -> list[str]:
    """Список доступных имён модулей (с алиасами)."""
    names = list(MODULES.keys())
    for alias, target in _ALIASES.items():
        if target in MODULES and alias not in names:
            names.append(alias)
    return sorted(names)


def _remove_module(module_name: str, *, auto_commit: bool = True) -> None:
    """Удаляет все директории модуля."""
    key = _resolve_name(module_name)

    if key not in MODULES:
        print(f"❌ Unknown module: {module_name}")
        print(f"   Available: {', '.join(_available_names())}")
        sys.exit(1)

    paths = _all_paths(key)
    removed = 0

    for rel_path in paths:
        full_path = PROJECT_ROOT / rel_path
        if not full_path.exists():
            print(f"⚠️  {rel_path} not found — skipping")
            continue

        safe_rmtree(full_path)
        print(f"🗑️  Removed: {rel_path}")
        removed += 1

    if not removed:
        print(f"\n📦 Module '{module_name}' — nothing to remove (not installed).")
        return

    # Git commit
    if auto_commit:
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Remove module: {MODULES[key].name}"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
            )
            print(f"\n📦 Module '{module_name}' removed and committed ({removed} paths).")
        except subprocess.CalledProcessError:
            print(f"\n📦 Module '{module_name}' removed ({removed} paths).")
            print("   ⚠️  Git commit failed — commit manually.")
    else:
        print(f"\n📦 Module '{module_name}' removed ({removed} paths).")

    print("   Restore with: python -m tools.init_project.add_module", module_name)


def main() -> None:
    print()
    print("═" * 45)
    print("  🗑️  Remove Module")
    print("═" * 45)
    print()

    if len(sys.argv) < 2:
        print("Usage: python -m tools.init_project.remove_module <module>")
        print()
        print("Available modules:")
        for key, cfg in MODULES.items():
            paths = cfg.src_dirs + cfg.deploy_dirs + cfg.doc_dirs
            aliases = [a for a, t in _ALIASES.items() if t == key]
            label = f"{key}" + (f" ({', '.join(aliases)})" if aliases else "")
            print(f"  {label:25s} → {', '.join(paths)}")
        sys.exit(0)

    module_name = sys.argv[1].lower()

    # Подтверждение
    key = _resolve_name(module_name)
    if key in MODULES:
        display = MODULES[key].name
        answer = input(f"❓ Remove {display}? This deletes all module files. [y/N] ")
        if answer.lower() not in ("y", "yes"):
            print("Cancelled.")
            sys.exit(0)

    no_commit = "--no-commit" in sys.argv
    _remove_module(module_name, auto_commit=not no_commit)


if __name__ == "__main__":
    main()
