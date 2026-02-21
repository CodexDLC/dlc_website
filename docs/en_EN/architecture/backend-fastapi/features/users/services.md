# 🧠 Business Logic (Services)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The service contains pure business logic. One public method often corresponds to one API endpoint.
The service manages transactions: calls `commit()` of the repository after successful execution of all operations.

## `AuthService`

### `register_user(schema: UserCreate) -> UserResponse`
1.  Check repository if email already exists (`get_by_email`).
    *   If exists — error `409 Conflict`.
2.  Hash password via security utility (`security.get_password_hash`).
3.  Call repository `create` with hash instead of password.
4.  **Commit:** Commit transaction (`repo.commit`).
5.  Return created user.

### `authenticate_user(schema: UserLogin) -> TokenSchema`
1.  Find user by email (`get_by_email`).
    *   If not found — error `401 Unauthorized`.
2.  Verify password (`security.verify_password`).
    *   If mismatch — error `401 Unauthorized`.
3.  Generate **Access Token** (JWT stateless).
4.  Generate **Refresh Token** (random string).
5.  Save Refresh Token to DB via `ITokenRepository.create`.
6.  **Commit:** Commit transaction (`token_repo.commit`).
7.  Return token pair.

### `refresh_token(token: str) -> TokenSchema`
1.  Find token in DB (`ITokenRepository.get_by_token`).
    *   If not found — error `401 Unauthorized`.
2.  Check expiration (`expires_at`).
    *   If expired — delete token, commit (`commit`) and return error `401`.
3.  **Rotation:** Delete old token (`delete`).
4.  Generate new pair (Access + Refresh).
5.  Save new Refresh to DB.
6.  **Commit:** Commit transaction (delete old + create new).
7.  Return new pair.
