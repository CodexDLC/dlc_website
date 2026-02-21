{% raw %}
# 📄 Templates

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../../README.md)

This directory contains the HTML templates for the Django application.

## 📋 Overview

The project uses the standard Django Template Language (DTL). Templates are organized by feature or page type.

## 📂 Structure

| Directory | Description |
|:---|:---|
| **[home](./home/README.md)** | Homepage templates. |
| **[team](./team/README.md)** | Team page templates. |
| **[legal](./legal/README.md)** | Legal documents (Privacy Policy, Imprint). |
| **[contacts](./contacts/README.md)** | Contact page templates. |
| **[services](./services/README.md)** | Services page templates. |
| **[includes](./includes/README.md)** | Reusable snippets (headers, footers, components). |
| **Root Files** | `base.html` (Master layout), Error pages (`404.html`, `500.html`). |

## 🧩 Base Layout (`base.html`)

The `base.html` file defines the common structure of the website:
- `<head>` metadata and assets.
- Navigation bar.
- `{% block content %}` for child templates.
- Footer.
- Scripts.

## 🎨 Context Processors

Templates have access to global context via processors defined in `settings.py`:
- `site_settings`: Global configuration.
- `i18n`: Translation context.
- `auth`: User information.
{% endraw %}
