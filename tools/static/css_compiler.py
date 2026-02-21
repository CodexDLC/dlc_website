#!/usr/bin/env python3
"""
CSS Compiler для LILY Beauty Salon

Этот скрипт компилирует base.css в app.css, встраивая все @import
и минифицируя результат.

Использование:
    python tools/static/css_compiler.py

Требования:
    pip install csscompressor
"""

import re
from pathlib import Path


def read_css_file(file_path: Path, base_path: Path) -> str:
    """Читает CSS файл и возвращает его содержимое."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ Ошибка чтения {file_path}: {e}")
        return ""


def resolve_imports(css_content: str, base_path: Path) -> str:
    """
    Рекурсивно разрешает все @import в CSS.

    Заменяет строки вида:
    @import url('path/to/file.css');
    или
    @import url('path/to/file.css') screen and (max-width: 767px);

    на содержимое импортируемых файлов.
    """
    import_pattern = r"@import\s+url\(['\"](.+?)['\"]\)(?:\s+(.+?))?;"

    def replace_import(match):
        import_path = match.group(1)
        media_query = match.group(2)

        # Разрешаем путь относительно base_path
        full_path = (base_path / import_path).resolve()

        if not full_path.exists():
            print(f"⚠️  Файл не найден: {full_path}")
            return f"/* Import not found: {import_path} */"

        # Читаем содержимое импортируемого файла
        imported_content = read_css_file(full_path, full_path.parent)

        # Рекурсивно разрешаем вложенные импорты
        imported_content = resolve_imports(imported_content, full_path.parent)

        # Если есть media query, оборачиваем контент
        if media_query:
            return f"/* From {import_path} */\n@media {media_query} {{\n{imported_content}\n}}"

        return f"/* From {import_path} */\n{imported_content}"

    return re.sub(import_pattern, replace_import, css_content)


def remove_comments(css_content: str) -> str:
    """
    Удаляет все комментарии из CSS.
    """
    # Удаляем многострочные комментарии /* ... */
    css_content = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)
    return css_content


def minify_css(css_content: str) -> str:
    """
    Полная минификация CSS:
    - Удаляет комментарии
    - Удаляет лишние пробелы и переносы строк
    """
    # Удаляем комментарии
    css_content = remove_comments(css_content)

    # Удаляем лишние пробелы и переносы
    css_content = re.sub(r"\s+", " ", css_content)
    css_content = re.sub(r"\s*([{}:;,])\s*", r"\1", css_content)

    return css_content.strip()


def compile_css(base_css_path: Path, output_path: Path, minify: bool = False, remove_comments_only: bool = False):
    """
    Компилирует base.css в app.css.

    Args:
        base_css_path: Путь к base.css
        output_path: Путь для сохранения app.css
        minify: Полная минификация (удаляет комментарии + пробелы)
        remove_comments_only: Только удалить комментарии, сохранить форматирование
    """
    print("🔧 Компиляция CSS...")
    print(f"   Источник: {base_css_path}")
    print(f"   Выход: {output_path}")

    # Читаем base.css
    base_content = read_css_file(base_css_path, base_css_path.parent)

    if not base_content:
        print("❌ Не удалось прочитать base.css")
        return

    # Разрешаем все импорты
    compiled_content = resolve_imports(base_content, base_css_path.parent)

    # Обработка комментариев и минификация
    if minify:
        print("   Полная минификация...")
        compiled_content = minify_css(compiled_content)
    elif remove_comments_only:
        print("   Удаление комментариев...")
        compiled_content = remove_comments(compiled_content)

    # Добавляем заголовок
    header = f"""/*
 * LILY Beauty Salon - Compiled CSS
 * Generated automatically - DO NOT EDIT
 * Source: base.css
 * Minified: {minify}
 */

"""
    compiled_content = header + compiled_content

    # Сохраняем результат
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(compiled_content)

        # Показываем статистику
        original_size = len(base_content)
        compiled_size = len(compiled_content)
        print("✅ Готово!")
        print(f"   Размер: {compiled_size:,} байт")
        if minify or remove_comments_only:
            savings = original_size - compiled_size
            print(f"   Экономия: {savings:,} байт ({savings / original_size * 100:.1f}%)")

    except Exception as e:
        print(f"❌ Ошибка записи {output_path}: {e}")


def main():
    """Главная функция."""
    # Определяем пути относительно tools/static/css_compiler.py
    # .parent (static) -> .parent (tools) -> .parent (root)
    project_root = Path(__file__).parent.parent.parent
    css_dir = project_root / "src" / "backend_django" / "static" / "css"

    base_css = css_dir / "base.css"
    app_css = css_dir / "app.css"

    if not base_css.exists():
        print(f"❌ Файл не найден: {base_css}")
        return

    # Компилируем с удалением комментариев (сохраняя читаемость)
    compile_css(base_css, app_css, minify=False, remove_comments_only=True)


if __name__ == "__main__":
    main()
