# 📜 Security Module

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

**File:** `src/backend-fastapi/core/security.py`

This module contains utilities for security: password hashing and access token generation.

## Functions

### `get_password_hash(password: str) -> str`

Hashes a password using the **Bcrypt** algorithm.

*   Used during user registration.

### `verify_password(plain_password, hashed_password) -> bool`

Verifies if the entered password matches the hash from the database.

*   Used during login.

### `create_access_token(subject, expires_delta) -> str`

Generates a **JWT (JSON Web Token)**.

*   `subject`: Usually the User ID.
*   `expires_delta`: Token lifetime (default is 30 minutes).
*   Signing Algorithm: `HS256`.
