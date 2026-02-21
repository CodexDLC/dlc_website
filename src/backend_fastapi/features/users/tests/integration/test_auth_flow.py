import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_flow_full_cycle(async_client: AsyncClient) -> None:
    """
    Полный цикл: Регистрация -> Логин -> Профиль -> Рефреш -> Логаут
    """
    email = "flow_user@example.com"
    password = "securePassword123!"

    # 1. Register
    response = await async_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert "id" in data

    # 2. Login
    response = await async_client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 3. Get Me (Profile)
    response = await async_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    profile = response.json()
    assert profile["email"] == email

    # FIX: Wait 1 second to ensure token 'exp' changes
    await asyncio.sleep(1.1)

    # 4. Refresh Token
    response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    new_tokens = response.json()
    assert new_tokens["access_token"] != access_token
    new_access_token = new_tokens["access_token"]

    # 5. Check Old Access Token (Should still be valid until expiration, but let's check new one)
    response = await async_client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert response.status_code == 200

    # 6. Logout
    # Assuming logout endpoint takes refresh token to invalidate it
    # Check API spec: usually logout invalidates the refresh token
    response = await async_client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    # If logout is implemented as 204 or 200
    assert response.status_code in [200, 204]

    # 7. Try Refresh with Old Token (Should Fail)
    response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_protected_route_without_token(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == 401
