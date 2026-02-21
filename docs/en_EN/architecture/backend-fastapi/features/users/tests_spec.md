# 🧪 Testing Strategy: Users Feature

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

## 🎯 Philosophy and Goals

**Main Goal:** Ensure security and reliability of the authentication system. Errors here are unacceptable as they lead to data leaks or login failures.

**Principles:**
1.  **Security First:** Tests must cover negative scenarios (wrong password, expired token, hacking attempts).
2.  **Isolation:** Unit tests of services do not depend on real DB.
3.  **Flows:** Integration tests verify full user scenarios.

## 📊 Testing Pyramid

### 1. Unit Tests (Services)
Isolated verification of `AuthService` business logic.
*   **Scope:** Password hashing, token generation, business rule validation (unique email).
*   **Mocking:** `IUserRepository`, `ITokenRepository`, `security` utils.
*   **Location:** `src/backend-fastapi/features/users/tests/unit/`

### 2. Integration Tests (API)
Verification of API endpoints with test DB (SQLite/Postgres).
*   **Scope:** `AuthRouter`, `UserRouter`.
*   **Focus:** HTTP response codes, Pydantic schema validation, Middleware operation.
*   **Location:** `src/backend-fastapi/features/users/tests/integration/`

---

## 🧪 Unit Testing Specifications

### `AuthService`
**File:** `src/backend-fastapi/features/users/tests/unit/test_auth_service.py`

**Scenarios:**
*   **Registration:**
    *   `test_register_success`: Successful registration (check `repo.create` call with hash).
    *   `test_register_duplicate_email`: Error if email taken (Mock repo returns User).
*   **Authentication:**
    *   `test_login_success`: Correct password -> tokens returned.
    *   `test_login_wrong_password`: Wrong password -> `AuthException`.
    *   `test_login_user_not_found`: Email not found -> error.
*   **Tokens:**
    *   `test_refresh_token_success`: Valid refresh -> new token pair.
    *   `test_refresh_token_expired`: Expired refresh -> error + token deletion.
    *   `test_refresh_token_reuse_detection` (Optional): If implemented, check for reuse.

---

## 🔗 Integration Testing Specifications

### `Auth Flow`
**File:** `src/backend-fastapi/features/users/tests/integration/test_auth_flow.py`

**Goal:** Verify full user lifecycle.

**Test Steps:**
1.  **Register:** POST `/auth/register` -> 201 Created.
2.  **Login:** POST `/auth/login` -> 200 OK + Tokens.
3.  **Me:** GET `/users/me` with Access Token -> 200 OK + Profile data.
4.  **Refresh:** POST `/auth/refresh` -> 200 OK + New tokens.
5.  **Old Token:** GET `/users/me` with old Access Token -> 401 Unauthorized (after expiration).
6.  **Logout:** POST `/auth/logout` -> 204 No Content.
7.  **Refresh after Logout:** POST `/auth/refresh` -> 401 Unauthorized.

### `Security Cases`
**File:** `src/backend-fastapi/features/users/tests/integration/test_security.py`

**Scenarios:**
*   Attempt access to `/users/me` without token -> 401.
*   Attempt access with fake token (wrong signature) -> 401.
*   SQL Injection in email field (verify ORM escapes it).

---

## 🛠️ Fixtures & Mocks

*   `mock_user_repo`: Async mock of user repository.
*   `mock_token_repo`: Async mock of token repository.
*   `user_payload`: Registration data (email, password).
*   `auth_headers(token)`: Helper to form `Authorization: Bearer ...` header.
