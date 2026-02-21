{% raw %}
# 🎨 CSS Architecture

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

Modular style structure for LILY Beauty Salon.

## 📁 Structure

```
css/
├── app.css                     # Main production file (compiled)
├── base.css                    # Main development file with @import and media queries
├── base/                       # Base styles
│   ├── variables.css           # CSS variables (colors, fonts)
│   ├── reset.css               # Style reset + fonts
│   ├── layout.css              # Main layout (container, site-wrapper)
│   ├── header.css              # Header and navigation
│   └── footer.css              # Footer
├── components/                 # Reusable components
│   ├── buttons.css             # Buttons
│   ├── cards.css               # Cards (bento, master-card, owner-block)
│   └── utils.css               # Utilities
├── pages/                      # Page-specific styles
│   ├── home.css                # Homepage
│   ├── services.css            # Services (price list)
│   ├── service-detail.css      # Service detail page
│   ├── team.css                # Team page
│   ├── contacts.css            # Contacts page
│   └── errors.css              # Error pages (404, 500)
└── adaptive/                   # Adaptive styles (Media Queries)
    ├── tablet.css              # 768px - 1024px
    └── mobile.css              # < 768px
```

## 🔧 Usage

### Development

In development mode, **`base.css`** is used with `@import` and media queries:

```html
<link rel="stylesheet" href="{% static 'css/base.css' %}">
```

The browser loads all modules separately (convenient for debugging).

### Production

For production, **`app.css`** is used - the compiled version:

```html
<link rel="stylesheet" href="{% static 'css/app.css' %}">
```

All `@import`s are resolved, media queries are inlined, and the code is minified.

## 🚀 Compilation

To compile `base.css` → `app.css`:

```bash
python tools/css_compiler.py
```

The script:
- Resolves all `@import` statements
- Inlines media queries
- Minifies the code (optional)

## 📝 Rules

### 1. Separation of Concerns

- **base/** - only base, global styles
- **components/** - reusable components
- **pages/** - page-specific styles
- **adaptive/** - only media queries

### 2. Naming

- **BEM** for components: `.card__title`, `.btn--primary`
- **Utilities** with prefix: `.text-center`, `.link-dashed`
- **Layout** without prefixes: `.container`, `.section`

### 3. CSS Variables

All colors, fonts, and sizes are in `base/variables.css`:

```css
:root {
    --color-emerald: #003831;
    --color-gold: #EDD071;
    --font-serif: 'Playfair Display', serif;
    --container-width: 1200px;
}
```

### 4. Media Queries

All adaptive styles reside **only** in `adaptive/`:

```css
/* ❌ DO NOT DO THIS: */
.hero-heading {
    font-size: 68px;
}
@media (max-width: 767px) {
    .hero-heading {
        font-size: 40px;
    }
}

/* ✅ DO THIS: */
/* pages/home.css */
.hero-heading {
    font-size: 68px;
}

/* adaptive/mobile.css */
.hero-heading {
    font-size: 40px;
}
```

## 🎨 Workflow

1. **Develop** - edit modules in `base/`, `components/`, `pages/`
2. **Test** - via `base.css` (with `@import`)
3. **Compile** - `python tools/css_compiler.py`
4. **Deploy** - use `app.css`

## 🔍 Debugging

If styles are not applied:

1. Check if `app.css` is included in `_meta.html`
2. Clear browser cache (`Ctrl+Shift+R`)
3. Check `collectstatic`: `python manage.py collectstatic --noinput`
4. Check paths in `@import` in `base.css`

## 📦 Production Build

```bash
# 1. Compile CSS
python tools/css_compiler.py

# 2. Collect static files
python src/backend_django/manage.py collectstatic --noinput

# 3. (Optional) Minify
# Uncomment lines in css_compiler.py for app.min.css
```
{% endraw %}
