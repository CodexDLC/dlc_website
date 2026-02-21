# ⚠️ Exceptions Module

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

**File:** `src/backend-fastapi/core/exceptions.py`

This module defines base exception classes and the global error handler.

## 📦 Response Format (JSON)

All API errors are returned in a unified format. The frontend should always expect an `error` field.

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid email format",
    "fields": ["email"]  // Optional, depends on error type
  }
}
```

## 🚦 Frontend Handling Guide

How the frontend should react to different error codes:

| HTTP Code | Error Code (`code`) | Description | Frontend Reaction (UX) |
| :--- | :--- | :--- | :--- |
| **401** | `auth_error` | Token invalid or expired. | 1. Try to refresh token.<br>2. If failed — **Redirect to /login**. |
| **403** | `permission_denied` | Insufficient rights (e.g., deleting someone else's image). | Show toast notification: *"You do not have permission for this action"*. |
| **404** | `not_found` | Resource not found. | **Page:** Show 404 component.<br>**List:** Show "Nothing found". |
| **409** | `business_conflict` | Conflict (e.g., email taken). | Show error under the specific field or a general Alert. |
| **422** | `validation_error` | Data validation error. | **Highlight fields in red.**<br>The `extra.fields` field contains the list of invalid fields. |
| **500** | `server_error` | Internal Server Error. | Show a generic "Something went wrong" screen. |

## 🐍 Exception Classes (Backend)

*   **`BaseAPIException`**: Parent class.
*   **`NotFoundException` (404)**: `error_code="not_found"`
*   **`ValidationException` (422)**: `error_code="validation_error"`
*   **`BusinessLogicException` (409)**: `error_code="business_conflict"`
*   **`PermissionDeniedException` (403)**: `error_code="permission_denied"`
*   **`AuthException` (401)**: `error_code="auth_error"`

## Usage in Code

```python
from app.core.exceptions import NotFoundException, BusinessLogicException

# Example 1: Not Found
if not user:
    raise NotFoundException(detail="User not found")

# Example 2: Conflict
if user_exists:
    raise BusinessLogicException(detail="Email already registered")
```
