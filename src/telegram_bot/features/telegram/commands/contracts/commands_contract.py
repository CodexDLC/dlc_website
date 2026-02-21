"""
Контракт для фичи commands.
Определяет Protocol для доступа к данным (через API или напрямую в БД).
"""

from typing import Protocol

from src.shared.schemas.user import UserUpsertDTO


class AuthDataProvider(Protocol):
    """
    Контракт доступа к данным аутентификации.
    Реализация подставляется через DI (container):
    - AuthClient (режим API) — HTTP запросы к FastAPI
    - AuthRepository (режим Direct) — прямой доступ к БД
    """

    async def upsert_user(self, user_dto: UserUpsertDTO) -> None: ...

    async def logout(self, user_id: int) -> None: ...
