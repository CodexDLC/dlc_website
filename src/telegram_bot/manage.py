import argparse
import sys
from pathlib import Path

# Путь к шаблонам
TEMPLATES_DIR = Path(__file__).parent / "resources" / "templates" / "feature"


def load_template(name: str) -> str:
    """Загружает шаблон из файла .py.tpl."""
    path = TEMPLATES_DIR / f"{name}.py.tpl"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def get_template_content(base_name: str, suffix: str = "") -> str:
    """Пытается загрузить специфичный шаблон, иначе берет базовый."""
    try:
        return load_template(f"{base_name}{suffix}")
    except FileNotFoundError:
        return load_template(base_name)


def create_feature(name: str, feature_type: str):
    """Создает структуру новой фичи на основе шаблонов."""
    base_path = Path(__file__).parent / "features" / feature_type / name

    if base_path.exists():
        print(f"❌ Ошибка: Фича '{name}' уже существует в папке features/{feature_type}/")
        return

    # Преобразование имен
    class_name = "".join(word.capitalize() for word in name.split("_"))
    feature_key = name.lower()
    container_key = f"redis_{feature_key}" if feature_type == "redis" else feature_key

    # Проверка на наличие "пары"
    other_type = "redis" if feature_type == "telegram" else "telegram"
    has_pair = (Path(__file__).parent / "features" / other_type / name).exists()

    # Структура папок
    dirs = [
        base_path,
        base_path / "handlers",
        base_path / "logic",
        base_path / "ui",
        base_path / "resources",
        base_path / "contracts",
        base_path / "tests",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        (d / "__init__.py").write_text("", encoding="utf-8")

    # Выбор шаблонов
    suffix = "_redis" if feature_type == "redis" else ""

    try:
        templates = {
            "feature.py": get_template_content("feature", suffix),
            "handlers.py": get_template_content("handlers", suffix),
            "orchestrator.py": get_template_content("orchestrator", suffix),
            "ui.py": get_template_content("ui"),
            "contract.py": get_template_content("contract"),
            "texts.py": get_template_content("texts"),
            "keyboards.py": get_template_content("keyboards"),
            "callbacks.py": get_template_content("callbacks"),
            "formatters.py": get_template_content("formatters"),
            "dto.py": get_template_content("dto"),
        }
    except FileNotFoundError as e:
        print(f"❌ Ошибка: Не найден файл шаблона. {e}")
        return

    # Создаем файлы
    files = {
        base_path / "feature_setting.py": templates["feature.py"],
        base_path / "handlers" / "handlers.py": templates["handlers.py"],
        base_path / "logic" / "orchestrator.py": templates["orchestrator.py"],
        base_path / "ui" / "ui.py": templates["ui.py"],
        base_path / "contracts" / "contract.py": templates["contract.py"],
        base_path / "resources" / "texts.py": templates["texts.py"],
        base_path / "resources" / "keyboards.py": templates["keyboards.py"],
        base_path / "resources" / "callbacks.py": templates["callbacks.py"],
        base_path / "resources" / "formatters.py": templates["formatters.py"],
        base_path / "resources" / "dto.py": templates["dto.py"],
    }

    for path, template in files.items():
        content = template.format(
            class_name=class_name, feature_key=feature_key, container_key=container_key, feature_type=feature_type
        )
        path.write_text(content, encoding="utf-8")

    # Экспорт роутера
    init_content = f"from .handlers import {'redis_router' if feature_type == 'redis' else 'router'}\n"
    (base_path / "handlers" / "__init__.py").write_text(init_content, encoding="utf-8")

    print(f"\n✅ Фича '{name}' ({feature_type}) успешно создана!")
    if has_pair:
        print(f"🔗 Найдена парная фича в '{other_type}'!")
        if feature_type == "telegram":
            print(
                "💡 Совет: Настрой наследование в resources/callbacks.py, чтобы обрабатывать кнопки из Redis-уведомлений."
            )

    setting_list = "INSTALLED_FEATURES" if feature_type == "telegram" else "INSTALLED_REDIS_FEATURES"
    print(f"👉 Добавь 'features.{feature_type}.{name}' в {setting_list} (settings.py)")


def main():
    parser = argparse.ArgumentParser(
        description="🛠 CodexDLC: Aiogram Bot Management Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")
    create_parser = subparsers.add_parser("create_feature", help="Создать новую фичу")
    create_parser.add_argument("name", help="Название фичи в snake_case")
    create_parser.add_argument("--type", choices=["telegram", "redis"], default="telegram")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if args.command == "create_feature":
        if not args.name:
            create_parser.print_help()
        else:
            create_feature(args.name, args.type)


if __name__ == "__main__":
    main()
