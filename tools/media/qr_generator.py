"""
QR Code Generator — GUI для создания стилизованных QR-кодов.

Запуск:
  python tools/media/qr_generator.py

Возможности:
  - Настройка цветов (foreground, background, прозрачность)
  - Встраивание логотипа
  - Экспорт PNG / WebP / SVG
  - Генерация singleton-класса (qr_style.py) с зафиксированным стилем

Зависимости: segno, Pillow, tkinter (встроен в Python)
"""

from __future__ import annotations

import io
import textwrap
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

import segno
from PIL import Image, ImageDraw, ImageTk

SCRIPT_DIR = Path(__file__).resolve().parent

ERROR_LEVELS = {
    "L (7%)": "L",
    "M (15%)": "M",
    "Q (25%)": "Q",
    "H (30%)": "H",
}


def _generate_qr(
    data: str,
    *,
    fg_color: str = "#000000",
    bg_color: str = "#ffffff",
    transparent: bool = False,
    error_level: str = "H (30%)",
    size: int = 400,
    logo_path: str | None = None,
) -> Image.Image:
    """Генерирует QR-код через segno с нативной прозрачностью."""
    error = ERROR_LEVELS.get(error_level, "H")

    qr = segno.make(data, error=error)

    # Вычисляем scale чтобы получить нужный размер
    modules = qr.symbol_size()[0]  # кол-во модулей (с border)
    scale = max(1, size // modules)

    # Фон: None = прозрачный (segno нативно)
    light = None if transparent else bg_color

    # Рендерим в PNG → BytesIO → Pillow
    buf = io.BytesIO()
    qr.save(buf, kind="png", dark=fg_color, light=light, scale=scale, border=2)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")

    # Ресайз до точного размера
    if img.size[0] != size:
        img = img.resize((size, size), Image.LANCZOS)

    # Логотип
    if logo_path and Path(logo_path).exists():
        logo = Image.open(logo_path).convert("RGBA")
        logo_size = size // 4
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

        # Белый круг под лого
        mask = Image.new("RGBA", (logo_size + 20, logo_size + 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(mask)
        draw.ellipse([0, 0, logo_size + 19, logo_size + 19], fill=(255, 255, 255, 255))

        pos_mask = ((size - logo_size - 20) // 2, (size - logo_size - 20) // 2)
        img.paste(mask, pos_mask, mask)

        pos_logo = ((size - logo_size) // 2, (size - logo_size) // 2)
        img.paste(logo, pos_logo, logo)

    return img


class QRGeneratorApp:
    """Tkinter GUI для генерации QR-кодов."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("QR Code Generator")
        self.root.geometry("750x650")
        self.root.resizable(False, False)

        # State
        self.fg_color = "#1a1a2e"
        self.bg_color = "#ffffff"
        self.logo_path: str | None = None
        self.preview_image: ImageTk.PhotoImage | None = None
        self.current_qr: Image.Image | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Строит интерфейс."""
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # ── Left panel: controls ──
        left = ttk.LabelFrame(main, text="Settings", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Data
        ttk.Label(left, text="Data (URL/text):").pack(anchor=tk.W)
        self.data_var = tk.StringVar(value="https://example.com")
        ttk.Entry(left, textvariable=self.data_var, width=30).pack(fill=tk.X, pady=(0, 8))

        # Foreground color
        fg_frame = ttk.Frame(left)
        fg_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(fg_frame, text="Foreground:").pack(side=tk.LEFT)
        self.fg_btn = tk.Button(
            fg_frame,
            bg=self.fg_color,
            width=4,
            relief=tk.RAISED,
            command=self._pick_fg_color,
        )
        self.fg_btn.pack(side=tk.RIGHT)
        self.fg_label = ttk.Label(fg_frame, text=self.fg_color)
        self.fg_label.pack(side=tk.RIGHT, padx=5)

        # Background color
        bg_frame = ttk.Frame(left)
        bg_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(bg_frame, text="Background:").pack(side=tk.LEFT)
        self.bg_btn = tk.Button(
            bg_frame,
            bg=self.bg_color,
            width=4,
            relief=tk.RAISED,
            command=self._pick_bg_color,
        )
        self.bg_btn.pack(side=tk.RIGHT)
        self.bg_label = ttk.Label(bg_frame, text=self.bg_color)
        self.bg_label.pack(side=tk.RIGHT, padx=5)

        # Transparent
        self.transparent_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Transparent background", variable=self.transparent_var).pack(
            anchor=tk.W,
            pady=(0, 8),
        )

        # Error correction
        ttk.Label(left, text="Error correction:").pack(anchor=tk.W)
        self.error_var = tk.StringVar(value="H (30%)")
        error_combo = ttk.Combobox(
            left,
            textvariable=self.error_var,
            values=list(ERROR_LEVELS.keys()),
            state="readonly",
            width=27,
        )
        error_combo.pack(fill=tk.X, pady=(0, 8))

        # Size
        ttk.Label(left, text="Size (px):").pack(anchor=tk.W)
        self.size_var = tk.IntVar(value=400)
        size_frame = ttk.Frame(left)
        size_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Scale(
            size_frame,
            from_=100,
            to=2000,
            variable=self.size_var,
            orient=tk.HORIZONTAL,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(size_frame, textvariable=self.size_var, width=5).pack(side=tk.RIGHT)

        # Logo
        logo_frame = ttk.Frame(left)
        logo_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(logo_frame, text="Choose Logo", command=self._pick_logo).pack(side=tk.LEFT)
        ttk.Button(logo_frame, text="Clear", command=self._clear_logo).pack(side=tk.LEFT, padx=5)
        self.logo_label = ttk.Label(left, text="No logo", foreground="gray")
        self.logo_label.pack(anchor=tk.W, pady=(0, 8))

        # ── Buttons ──
        ttk.Separator(left).pack(fill=tk.X, pady=5)

        ttk.Button(left, text="Preview", command=self._preview).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Save PNG", command=lambda: self._save("png")).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Save WebP", command=lambda: self._save("webp")).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Save SVG", command=self._save_svg).pack(fill=tk.X, pady=2)

        ttk.Separator(left).pack(fill=tk.X, pady=5)

        ttk.Button(
            left,
            text="Export Style Class",
            command=self._export_style,
        ).pack(fill=tk.X, pady=2)

        # ── Right panel: preview ──
        right = ttk.LabelFrame(main, text="Preview", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.preview_label = ttk.Label(right, text="Click Preview\nto generate QR", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)

    # ─────────────────────────────────────────
    # Color pickers
    # ─────────────────────────────────────────

    def _pick_fg_color(self) -> None:
        color = colorchooser.askcolor(initialcolor=self.fg_color, title="Foreground Color")
        if color[1]:
            self.fg_color = color[1]
            self.fg_btn.configure(bg=self.fg_color)
            self.fg_label.configure(text=self.fg_color)

    def _pick_bg_color(self) -> None:
        color = colorchooser.askcolor(initialcolor=self.bg_color, title="Background Color")
        if color[1]:
            self.bg_color = color[1]
            self.bg_btn.configure(bg=self.bg_color)
            self.bg_label.configure(text=self.bg_color)

    def _pick_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Logo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")],
        )
        if path:
            self.logo_path = path
            self.logo_label.configure(text=Path(path).name, foreground="black")

    def _clear_logo(self) -> None:
        self.logo_path = None
        self.logo_label.configure(text="No logo", foreground="gray")

    # ─────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────

    def _get_params(self) -> dict:
        """Собирает текущие параметры."""
        return {
            "data": self.data_var.get(),
            "fg_color": self.fg_color,
            "bg_color": self.bg_color,
            "transparent": self.transparent_var.get(),
            "error_level": self.error_var.get(),
            "size": self.size_var.get(),
            "logo_path": self.logo_path,
        }

    def _preview(self) -> None:
        """Генерирует и показывает QR в preview."""
        params = self._get_params()
        if not params["data"].strip():
            messagebox.showwarning("Warning", "Enter data/URL first")
            return

        try:
            self.current_qr = _generate_qr(**params)

            # Resize for preview (max 400x400)
            preview = self.current_qr.copy()
            preview.thumbnail((400, 400), Image.LANCZOS)

            # Checkerboard background for transparent
            if params["transparent"]:
                checker = _checkerboard(preview.size)
                checker.paste(preview, mask=preview)
                preview = checker

            self.preview_image = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview_image, text="")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _save(self, fmt: str) -> None:
        """Сохраняет QR в PNG/WebP."""
        if self.current_qr is None:
            self._preview()
        if self.current_qr is None:
            return

        filetypes = {"png": ("PNG", "*.png"), "webp": ("WebP", "*.webp")}
        ft = filetypes.get(fmt, filetypes["png"])

        path = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=[(ft[0], ft[1]), ("All", "*.*")],
            initialfile=f"qrcode.{fmt}",
        )
        if not path:
            return

        if fmt == "webp":
            self.current_qr.convert("RGB").save(path, "WebP", quality=90)
        else:
            self.current_qr.save(path, "PNG")

        messagebox.showinfo("Saved", f"QR saved: {path}")

    def _save_svg(self) -> None:
        """Сохраняет QR как SVG (segno нативно)."""
        params = self._get_params()
        if not params["data"].strip():
            messagebox.showwarning("Warning", "Enter data/URL first")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG", "*.svg"), ("All", "*.*")],
            initialfile="qrcode.svg",
        )
        if not path:
            return

        error = ERROR_LEVELS.get(params["error_level"], "H")
        qr = segno.make(params["data"], error=error)
        light = None if params["transparent"] else params["bg_color"]
        qr.save(path, kind="svg", dark=params["fg_color"], light=light, scale=10, border=2)

        messagebox.showinfo("Saved", f"SVG saved: {path}")

    def _export_style(self) -> None:
        """Генерирует qr_style.py с текущими настройками (segno-based)."""
        params = self._get_params()

        ec_map = {"L (7%)": "L", "M (15%)": "M", "Q (25%)": "Q", "H (30%)": "H"}
        ec_letter = ec_map.get(params["error_level"], "H")

        bg_value = "None" if params["transparent"] else f'"{params["bg_color"]}"'
        logo_comment = ""
        if params["logo_path"]:
            logo_comment = f"\n    # Logo used during export: {params['logo_path']}"

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        code = textwrap.dedent(f'''\
            """
            QR Code Style — singleton for project-branded QR codes.

            Generated: {now}
            Generator: python tools/media/qr_generator.py

            Usage:
                from tools.media.qr_style import qr_style

                # PIL Image
                img = qr_style.generate("https://example.com")
                img.save("qr.png")

                # Custom size
                img = qr_style.generate("https://t.me/mybot", size=200)

                # Bytes for bot/API
                data = qr_style.to_bytes("https://example.com", fmt="webp")
            """

            from __future__ import annotations

            import io
            from pathlib import Path

            import segno
            from PIL import Image, ImageDraw


            class QRStyle:
                """Singleton with fixed QR code style for the project."""

                _instance = None

                # ── Style settings (locked at export) ──
                FOREGROUND = "{params["fg_color"]}"
                BACKGROUND = {bg_value}
                ERROR_CORRECTION = "{ec_letter}"
                DEFAULT_SIZE = {params["size"]}{logo_comment}

                def __new__(cls) -> "QRStyle":
                    if cls._instance is None:
                        cls._instance = super().__new__(cls)
                    return cls._instance

                def generate(
                    self,
                    data: str,
                    *,
                    size: int | None = None,
                    logo: str | Path | None = None,
                ) -> Image.Image:
                    """Generate QR code in project style.

                    Args:
                        data: Text or URL to encode.
                        size: Output size in pixels (default: DEFAULT_SIZE).
                        logo: Path to logo image (optional).

                    Returns:
                        PIL Image in RGBA.
                    """
                    _size = size or self.DEFAULT_SIZE

                    qr = segno.make(data, error=self.ERROR_CORRECTION)
                    modules = qr.symbol_size()[0]
                    scale = max(1, _size // modules)

                    buf = io.BytesIO()
                    qr.save(
                        buf, kind="png",
                        dark=self.FOREGROUND,
                        light=self.BACKGROUND,
                        scale=scale,
                        border=2,
                    )
                    buf.seek(0)
                    img = Image.open(buf).convert("RGBA")

                    if img.size[0] != _size:
                        img = img.resize((_size, _size), Image.LANCZOS)

                    if logo:
                        logo_img = Image.open(logo).convert("RGBA")
                        logo_s = _size // 4
                        logo_img = logo_img.resize((logo_s, logo_s), Image.LANCZOS)

                        mask = Image.new("RGBA", (logo_s + 20, logo_s + 20), (0, 0, 0, 0))
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse([0, 0, logo_s + 19, logo_s + 19], fill=(255, 255, 255, 255))

                        pos_m = ((_size - logo_s - 20) // 2, (_size - logo_s - 20) // 2)
                        img.paste(mask, pos_m, mask)
                        pos_l = ((_size - logo_s) // 2, (_size - logo_s) // 2)
                        img.paste(logo_img, pos_l, logo_img)

                    return img

                def to_bytes(
                    self,
                    data: str,
                    *,
                    fmt: str = "png",
                    size: int | None = None,
                    logo: str | Path | None = None,
                ) -> bytes:
                    """Generate QR and return bytes (for bot/API).

                    Args:
                        data: Text or URL.
                        fmt: Format — "png" or "webp".
                        size: Output size in pixels.
                        logo: Path to logo image.

                    Returns:
                        Image bytes.
                    """
                    img = self.generate(data, size=size, logo=logo)
                    buf = io.BytesIO()
                    if fmt == "webp":
                        img.convert("RGB").save(buf, "WebP", quality=90)
                    else:
                        img.save(buf, "PNG")
                    return buf.getvalue()


            # Singleton instance
            qr_style = QRStyle()
        ''')

        output_path = SCRIPT_DIR / "qr_style.py"
        output_path.write_text(code, encoding="utf-8")
        messagebox.showinfo(
            "Exported",
            "Style class saved:\\n{output_path}\\n\\n"
            "Usage:\\n  from tools.media.qr_style import qr_style\\n"
            "  img = qr_style.generate('https://example.com')",
        )

    def run(self) -> None:
        self.root.mainloop()


def _checkerboard(size: tuple[int, int], block: int = 10) -> Image.Image:
    """Шахматный фон для визуализации прозрачности."""
    img = Image.new("RGBA", size, (200, 200, 200, 255))
    draw = ImageDraw.Draw(img)
    for y in range(0, size[1], block):
        for x in range(0, size[0], block):
            if (x // block + y // block) % 2 == 0:
                draw.rectangle([x, y, x + block, y + block], fill=(255, 255, 255, 255))
    return img


def main() -> None:
    app = QRGeneratorApp()
    app.run()


if __name__ == "__main__":
    main()
