"""
Add Module — восстановление модулей из git истории.

После установки первый коммит "Install" содержит ВСЕ файлы шаблона.
Эта команда достаёт нужный модуль обратно:

  python -m tools.init_project.add_module bot
  python -m tools.init_project.add_module fastapi
  python -m tools.init_project.add_module django

Работает через: git checkout <install-hash> -- <paths>
Без интернета, всё из локальной git истории.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.init_project.config import MODULES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Алиасы для удобства: "bot" → "telegram_bot"
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


def _get_install_hash() -> str | None:
    """Читает hash коммита 'Install' из файла."""
    hash_file = PROJECT_ROOT / ".template_install_hash"
    if hash_file.exists():
        return hash_file.read_text(encoding="utf-8").strip()

    # Fallback: ищем по сообщению коммита
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--oneline", "--grep=Install: template snapshot"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split()[0]
    except FileNotFoundError:
        pass

    return None


def _restore_module(module_name: str) -> None:
    """Восстанавливает модуль из коммита Install."""
    key = _resolve_name(module_name)

    if key not in MODULES:
        print(f"❌ Unknown module: {module_name}")
        print(f"   Available: {', '.join(_available_names())}")
        sys.exit(1)

    install_hash = _get_install_hash()
    if not install_hash:
        print("❌ Install commit not found.")
        print("   This project may not have been created from the template.")
        sys.exit(1)

    paths = _all_paths(key)
    restored = 0

    for rel_path in paths:
        full_path = PROJECT_ROOT / rel_path
        if full_path.exists():
            print(f"⚠️  {rel_path} already exists — skipping")
            continue

        try:
            subprocess.run(
                ["git", "checkout", install_hash, "--", rel_path],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
            )
            print(f"✅ Restored: {rel_path}")
            restored += 1
        except subprocess.CalledProcessError:
            print(f"❌ Failed to restore: {rel_path}")
            print(f"   (not found in Install commit {install_hash[:8]})")

    print()
    if restored:
        print(f"📦 Module '{module_name}' restored ({restored} paths).")
        print("   Don't forget to update pyproject.toml dependencies and Docker config!")
    else:
        print(f"📦 Module '{module_name}' — nothing to restore (all paths already exist).")


def _available_names() -> list[str]:
    """Список доступных имён модулей (с алиасами)."""
    names = list(MODULES.keys())
    for alias, target in _ALIASES.items():
        if target in MODULES and alias not in names:
            names.append(alias)
    return sorted(names)


def main() -> None:
    print()
    print("═" * 45)
    print("  📦 Add Module from Template")
    print("═" * 45)
    print()

    if len(sys.argv) < 2:
        print("Usage: python -m tools.init_project.add_module <module>")
        print()
        print("Available modules:")
        for key, cfg in MODULES.items():
            paths = cfg.src_dirs + cfg.deploy_dirs + cfg.doc_dirs
            aliases = [a for a, t in _ALIASES.items() if t == key]
            label = f"{key}" + (f" ({', '.join(aliases)})" if aliases else "")
            print(f"  {label:25s} → {', '.join(paths)}")
        sys.exit(0)

    module_name = sys.argv[1].lower()
    _restore_module(module_name)


if __name__ == "__main__":
    main()
