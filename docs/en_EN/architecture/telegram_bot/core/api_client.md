# 📄 API Client

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The `BaseApiClient` is an asynchronous HTTP client wrapper built on top of `httpx`. It provides a standardized way for the Telegram Bot to communicate with external services (primarily the Django Backend API).

## 🏗️ Class: BaseApiClient

Located in: `src/telegram_bot/core/api_client.py`

### Constructor

```python
def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 10.0)
```

- **base_url**: The root URL of the API.
- **api_key**: Optional API key sent via `X-API-Key` header.
- **timeout**: Request timeout in seconds (default: 10.0).

### Methods

#### `_request` (Internal)
An asynchronous method to perform HTTP requests.

- **method**: HTTP method (GET, POST, etc.).
- **endpoint**: API endpoint path.
- **json**: Optional JSON payload.
- **params**: Optional query parameters.
- **Returns**: Parsed JSON data or raises `ApiClientError`.

## ⚠️ Error Handling

The client uses a custom exception `ApiClientError` to wrap various underlying issues:
- **HTTPStatusError**: Triggered for 4xx and 5xx responses.
- **RequestError**: Triggered for connection issues, timeouts, etc.
- **Unknown Error**: Any other unexpected exceptions.

## 📝 Usage Example

```python
client = BaseApiClient(base_url="https://api.example.com", api_key="secret")
data = await client._request("GET", "/v1/data")
```
