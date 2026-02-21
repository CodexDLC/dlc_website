# 📂 Telegram Bot Architecture

[⬅️ Back](../README.md) | [🏠 Docs Root](../../../README.md)

Documentation and development plans for the Telegram Bot application located in `src/telegram_bot`.

## 🗺️ Module Map

| Component | Description |
|:---|:---|
| **[📂 Core Infrastructure](./core/README.md)** | DI Container, Configuration, Settings, and Middleware |
| **[📂 Features (Modules)](./features/README.md)** | Modular business logic (Menu, Commands) |
| **[📂 Services](./services/README.md)** | Shared services (Director, FSM, Sender, Animation) |
| **[📂 Resources](./resources/README.md)** | Templates, Texts, and Keyboards |
| **[🗺️ Roadmap](./roadmap.md)** | Development plan and future features |

## 🏗️ Project Structure

Below is the structure of the `src/telegram_bot` directory.

### Application Code

```text
src/telegram_bot/
 ┣ 📂 core                  # Infrastructure Layer
 ┃ ┣ 📜 api_client.py       # Base HTTP Client (Abstract)
 ┃ ┣ 📜 config.py           # Environment Configuration (Pydantic)
 ┃ ┣ 📜 container.py        # DI Container (Services & Features assembly)
 ┃ ┣ 📜 factory.py          # Bot & Dispatcher Factory
 ┃ ┣ 📜 garbage_collector.py# Dynamic FSM Garbage Collector
 ┃ ┣ 📜 routers.py          # Router Auto-Discovery & Assembly
 ┃ ┗ 📜 settings.py         # INSTALLED_FEATURES & Middleware config
 ┃
 ┣ 📂 features              # Modular Features (Plugins)
 ┃ ┣ 📂 bot_menu            # Core Feature: Dashboard
 ┃ ┣ 📂 commands            # Core Feature: /start, /help
 ┃ ┗ 📂 errors              # Core Feature: Error Handling
 ┃
 ┣ 📂 services              # Shared Services
 ┃ ┣ 📂 director            # Navigation & Scene Management
 ┃ ┣ 📂 sender              # ViewSender (Smart Message Editing)
 ┃ ┣ 📂 fsm                 # State Managers & Base Classes
 ┃ ┣ 📂 feature_discovery   # Auto-discovery service (Menu, GC)
 ┃
 ┗ 📜 [app_telegram.py](./app_telegram.md) # Entry Point (Polling)
```

## 🛠️ Management Scripts

| Component | Description |
|:---|:---|
| **[📜 Feature Management Script](./manage_script.md)** | CLI tool for creating new features |

## 📦 Key Concepts

Quick access to architectural concepts.

*   **🧩 Feature-Based Architecture**
    *   Each feature is an isolated module with its own `feature_setting.py` manifest.
    *   Features are pluggable via `INSTALLED_FEATURES`.

*   **🎬 Director & Orchestrator**
    *   **Director:** Manages global navigation (switching between features).
    *   **Orchestrator:** Manages logic within a feature (Data -> UI).

*   **📱 Bot Menu (Dashboard)**
    *   A persistent "Dashboard" message.
    *   Buttons are auto-discovered from features via `MENU_CONFIG`.
