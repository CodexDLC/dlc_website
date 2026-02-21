# 🐍 Backend (Django)

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../README.md)

The backend is built with **Django**, following a modular "Feature-Sliced" inspired architecture.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[⚙️ Core](./core/README.md)** | Settings, WSGI/ASGI, and base configuration. |
| **[🧩 Features](./features/README.md)** | Business logic modules (apps). |
| **[🔌 API](./api/README.md)** | REST API implementation (Django Ninja). |
| **[📄 Templates](./templates/README.md)** | HTML templates. |
| **[🌍 Locale](./locale/README.md)** | Internationalization files. |
| **[🎨 Static](./static/README.md)** | CSS, JS, and images. |
| **[🖼️ Media](./media/README.md)** | User-uploaded content. |
| **[📜 manage.py](./manage.md)** | Django's command-line utility. |
| **[📂 logs](./logs/README.md)** | Directory for application logs. |
| **[📜 Staticfiles](./staticfiles.md)** | Collected static files for deployment. |
| **[📜 conftest.py](./conftest.md)** | Pytest configuration and fixtures. |
| **[📜 Backend README](./backend_readme.md)** | High-level overview of the Django backend project. |

## 🏗️ Architecture Overview

The project deviates from the standard flat Django structure to improve scalability:

1.  **Core:** Holds all infrastructure code (settings, urls).
2.  **Features:** Contains domain-specific logic. Each feature is a Django app.
3.  **API:** Centralized API definition using Django Ninja.

## 🚀 Getting Started

1.  **Install Dependencies:** `pip install -r requirements.txt`
2.  **Environment:** Copy `.env.example` to `.env` and configure.
3.  **Migrate:** `python manage.py migrate`
4.  **Run:** `python manage.py runserver`
