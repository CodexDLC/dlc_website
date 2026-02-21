# tools/media/

Утилиты для работы с медиафайлами.

## convert_to_webp.py

Массовая конвертация PNG/JPG в WebP. Оригиналы перемещаются в `_source/`.

```bash
# С аргументом
python tools/media/convert_to_webp.py src/backend_django/static/img

# Интерактивно (спросит путь)
python tools/media/convert_to_webp.py
```

**Что делает:**
- Рекурсивно находит все `.png`, `.jpg`, `.jpeg` в указанной папке
- Конвертирует в WebP (quality=80)
- Перемещает оригинал в подпапку `_source/` сохраняя структуру
- Пропускает файлы если WebP уже существует
- Не трогает файлы уже в `_source/`

---

## qr_generator.py

GUI-приложение для генерации стилизованных QR-кодов (Tkinter).

```bash
python tools/media/qr_generator.py
```

**Возможности:**
- Настройка цветов foreground/background
- Прозрачный фон
- Встраивание логотипа (с белым кружком под ним)
- Уровень коррекции ошибок (L/M/Q/H)
- Экспорт в PNG, WebP, SVG
- **Export Style Class** — генерирует `tools/media/qr_style.py` с зафиксированным стилем проекта

**qr_style.py** (генерируется через GUI):

```python
from tools.media.qr_style import qr_style

# PIL Image
img = qr_style.generate("https://example.com")
img.save("qr.png")

# Bytes для бота / API
data = qr_style.to_bytes("https://t.me/mybot", fmt="webp")
```

Зависимости: `segno`, `Pillow`, `tkinter` (встроен в Python).
