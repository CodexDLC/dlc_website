# 📜 Contracts (Repositories)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The feature folder (`contracts`) contains abstract classes (`Protocol`) describing database interaction methods. The implementation (SQLAlchemy) is hidden behind this interface.

## `IUserRepository`

Interface for working with users.

*   **`create(user_data: dict) -> User`**
    *   Create a new user record (without commit).
    *   Returns the user model.
*   **`get_by_email(email: str) -> Optional[User]`**
    *   Find user by email.
    *   Used to check for duplicates during registration and search during login.
*   **`get_by_id(user_id: UUID) -> Optional[User]`**
    *   Get user profile by ID (for `/me`).
*   **`commit() -> None`**
    *   Commit the current transaction.

## `ITokenRepository`

Interface for working with refresh tokens.

*   **`create(user_id: UUID, token: str, expires_at: datetime)`**
    *   Write a new refresh token to DB (without commit).
*   **`get_by_token(token: str) -> Optional[RefreshToken]`**
    *   Find token (check for existence and validity).
*   **`delete(token: str)`**
    *   Delete a specific token (logout / rotation).
*   **`delete_by_user(user_id: UUID)`**
    *   Logout user from all devices (delete all their tokens).
*   **`commit() -> None`**
    *   Commit the current transaction.
