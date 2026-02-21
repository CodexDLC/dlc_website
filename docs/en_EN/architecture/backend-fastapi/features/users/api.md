# 🔌 API Layer (Routers)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Endpoints should be as thin as possible. Their task is validation (Pydantic) and passing control to the service.

## Endpoints

### `POST /auth/register`
*   **Accepts:** `UserCreate` (email, password).
*   **Validation:** Pydantic (email format, password length).
*   **Action:** Calls `AuthService.register_user`.
*   **Returns:** `201 Created` + `UserResponse`.

### `POST /auth/login`
*   **Accepts:** `UserLogin` (email, password).
*   **Action:** Calls `AuthService.authenticate_user`.
*   **Returns:** `200 OK` + `TokenSchema` (access_token, refresh_token).

### `POST /auth/refresh`
*   **Accepts:** `RefreshTokenSchema` (refresh_token).
*   **Action:** Calls `AuthService.refresh_token`.
*   **Returns:** `200 OK` + `TokenSchema`.

### `GET /users/me`
*   **Requires:** `Depends(get_current_user)` — authorization via Bearer token.
*   **Action:** Returns current user profile.
*   **Returns:** `200 OK` + `UserResponse`.
