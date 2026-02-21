# 📄 Bot Configuration

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `BotSettings` class manages all environment variables and configuration for the Telegram Bot. It is built using `Pydantic Settings` and inherits from `CommonSettings`.

## 🏗️ Class: BotSettings

Located in: `src/telegram_bot/core/config.py`

### Key Configuration Fields

#### Bot & Telegram
- **bot_token**: Telegram Bot API token.
- **telegram_admin_channel_id**: ID of the channel where admin notifications are sent.
- **telegram_notification_topic_id**: Default topic ID for notifications (default: 1).
- **telegram_topics**: A dictionary mapping service categories to Telegram topic IDs. Parsed from a JSON string in `.env`.

#### Roles & Permissions
- **superuser_ids**: Comma-separated string of Telegram user IDs with superuser access.
- **owner_ids**: Comma-separated string of Telegram user IDs with owner access.
- **roles**: A property that returns a dictionary of roles (`superuser`, `owner`, `admin`) with their respective ID lists.

#### Data & Backend
- **BOT_DATA_MODE**: Determines how the bot fetches data.
    - `api`: Communicates with the Django backend via REST (default).
    - `direct`: Connects directly to its own database.
- **backend_api_url**: The base URL for the backend API. Automatically switches between `localhost` (debug) and `backend` (docker) if not explicitly set.
- **backend_api_key**: API key for backend authentication.
- **backend_api_timeout**: Timeout for API requests (default: 10.0s).

### Validators & Properties

- **parse_telegram_topics**: A validator that safely parses the `TELEGRAM_TOPICS` JSON string into a Python dictionary.
- **api_url**: A property that intelligently determines the backend URL based on the environment (Docker vs. Local).
- **superuser_ids_list / owner_ids_list**: Properties that convert comma-separated strings into lists of integers.

## 📝 .env Example

```env
BOT_TOKEN=123456789:ABCDEF...
TELEGRAM_ADMIN_CHANNEL_ID=-100123456789
TELEGRAM_TOPICS='{"hair": 2, "nails": 4}'
SUPERUSER_IDS=111222333,444555666
BACKEND_API_URL=http://backend:8000
BACKEND_API_KEY=your_secret_key
```
