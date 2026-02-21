# 🏷️ Naming Conventions

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../README.md)

Naming rules for the database.

## Tables

*   **Snake Case**: `users`, `refresh_tokens`, `user_profiles`.
*   **Plural**: Names in plural form (`users`, not `user`).

## Fields

*   **PK**: `id` (usually UUID or BigInt).
*   **FK**: `entity_id` (e.g., `user_id`, `image_id`).
*   **Boolean**: Prefix `is_` or `has_` (e.g., `is_active`, `has_access`).
*   **Date**: Suffix `_at` for timestamp (`created_at`) or `_date` for date.
