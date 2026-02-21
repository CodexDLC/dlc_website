# 🚩 Task: Refactor User Creation Flags

[⬅️ Back](../../README.md) | [🏠 Docs Root](../../../../../README.md)

**Status:** 📋 Backlog
**Priority:** Low
**Related Tech Debt:** Hardcoded User Flags

## 📝 Problem Description

In `UserRepository.create`, flag values are hardcoded:

```python
is_active=True
is_superuser=False
```

This makes it impossible to create inactive users (for email confirmation) or administrators via this method.

## 🎯 Goal

Make the user creation method flexible.

## 📋 Implementation Plan

1.  **Schema:** Add optional fields `is_active` and `is_superuser` to `UserCreate` (or create a separate DTO for repository).
2.  **Repository:** Accept these flags in `create` method and use them when creating `User` model.
3.  **Service:** In `AuthService.register_user`, explicitly pass required default values (Active=True, Superuser=False) to preserve current behavior for public registration.
