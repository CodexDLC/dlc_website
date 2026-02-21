from typing import Any

import httpx
from loguru import logger as log


class ApiClientError(Exception):
    """Базовая ошибка API клиента"""

    pass


class BaseApiClient:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            self.headers["X-API-Key"] = api_key

        # Таймаут передается извне (из конфига)
        self.timeout = httpx.Timeout(timeout, connect=5.0)

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                log.debug(f"API Request: {method} {url} | params={params} json={json}")
                response = await client.request(method=method, url=url, headers=self.headers, json=json, params=params)

                # Проверка статуса (выбросит исключение для 4xx/5xx)
                response.raise_for_status()

                # Парсинг ответа
                data = response.json()
                return data

            except httpx.HTTPStatusError as e:
                log.error(f"API Error {e.response.status_code}: {e.response.text}")
                raise ApiClientError(f"HTTP Error: {e.response.status_code}") from e
            except httpx.RequestError as e:
                log.error(f"API Connection Error: {e}")
                raise ApiClientError(f"Connection Error: {str(e)}") from e
            except Exception as e:
                log.exception(f"API Unknown Error: {e}")
                raise ApiClientError(f"Unknown Error: {str(e)}") from e
