# 📜 Feature Management Script (`manage.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This script (`src/telegram_bot/manage.py`) is a command-line utility designed to streamline the creation of new features for the Telegram bot. It automates the generation of the necessary folder structure and boilerplate code based on predefined templates, ensuring consistency and accelerating development.

## Purpose

The `manage.py` script acts as a development helper, allowing developers to quickly scaffold new "Telegram" or "Redis" features without manually creating all the required files and directories.

## Usage

To use the script, navigate to the `src/telegram_bot` directory in your terminal.

### `create_feature` Command

This command generates the basic structure for a new feature.

```bash
python manage.py create_feature <name> [--type {telegram,redis}]
```

*   `<name>`: The name of the feature, which should be in `snake_case` (e.g., `my_new_feature`). This name will be used to generate class names (e.g., `MyNewFeature`) and feature keys.
*   `--type {telegram,redis}`: Specifies the type of feature to create.
    *   `telegram` (default): Creates a UI-oriented feature that interacts directly with the Telegram API.
    *   `redis`: Creates a background feature that primarily interacts with Redis Streams.

### Examples

**Create a new Telegram feature named `user_profile`:**

```bash
python manage.py create_feature user_profile --type telegram
```

This will create the following structure:

```
src/telegram_bot/features/telegram/user_profile/
 ┣ 📂 handlers
 ┣ 📂 logic
 ┣ 📂 ui
 ┣ 📂 resources
 ┣ 📂 contracts
 ┣ 📂 tests
 ┣ 📜 feature_setting.py
 ┣ ... (other generated files)
```

**Create a new Redis feature named `analytics_events`:**

```bash
python manage.py create_feature analytics_events --type redis
```

This will create:

```
src/telegram_bot/features/redis/analytics_events/
 ┣ 📂 handlers
 ┣ 📂 logic
 ┣ 📂 ui
 ┣ 📂 resources
 ┣ 📂 contracts
 ┣ 📂 tests
 ┣ 📜 feature_setting.py
 ┣ ... (other generated files)
```

## How it Works

The script performs the following steps:

1.  **Loads Templates:** It reads `.py.tpl` files from `src/telegram_bot/resources/templates/feature` to get the boilerplate code for different components (orchestrator, UI, handlers, etc.).
2.  **Generates Names:** It converts the provided feature `name` into `class_name` (PascalCase) and `feature_key` (snake_case). For `redis` type features, it also generates a `container_key` with a `redis_` prefix.
3.  **Creates Directories:** It sets up the standard directory structure for the new feature (e.g., `handlers`, `logic`, `ui`).
4.  **Populates Files:** It fills the generated files with content from the templates, replacing placeholders like `{class_name}` and `{feature_key}`.
5.  **Exports Router:** For `telegram` features, it exports the `router` from `handlers/__init__.py`. For `redis` features, it exports `redis_router`.
6.  **Provides Instructions:** After successful creation, it prints instructions on how to add the new feature to `INSTALLED_FEATURES` or `INSTALLED_REDIS_FEATURES` in `src/telegram_bot/core/settings.py`.

## Template Customization

The script uses Jinja2-like templates (`.py.tpl` files). Developers can modify these templates to customize the generated code structure and content, ensuring that new features adhere to project-specific coding standards and patterns.
