# 🗄️ Database Schema (Users)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

## Table `users`

Represents a system user.

| Field | Type | Description |
| :--- | :--- | :--- |
| **id** | `UUID` (PK) | Automatically generated. Use: `mapped_column(Uuid, primary_key=True, default=uuid.uuid4)` |
| **email** | `String` (Unique, Index) | Main identifier for login. |
| **hashed_password** | `String` | Password hash (Bcrypt). Do not store plain passwords! |
| **is_active** | `Bool` | Activity flag (soft delete / ban). Default: `True`. |
| **is_superuser** | `Bool` | Administrator flag. Default: `False`. |
| **created_at** | `DateTime` | Registration date. |
| **updated_at** | `DateTime` | Last profile update date. |

## Table `social_accounts`

Linking external accounts (OAuth2) to a user. One user can have multiple social networks.

| Field | Type | Description |
| :--- | :--- | :--- |
| **id** | `BigInt` (PK) | Incremental ID. |
| **user_id** | `UUID` (FK -> users.id) | Account owner. `ON DELETE CASCADE`. |
| **provider** | `String` | Provider name (google, github, discord). |
| **provider_id** | `String` | Unique user ID in the provider's system (sub). |
| **email** | `String` (Optional) | Email received from the provider (for reference). |
| **created_at** | `DateTime` | Linking date. |

### Indexes for `social_accounts`:
- `idx_provider_pid` - Unique Index on pair `(provider, provider_id)` (protection against duplicates).
- `idx_user_id` - Index on field `user_id` (fast search for all user's social networks).

## Table `refresh_tokens`

Storage for active sessions (White List). Used to refresh Access Tokens.

| Field | Type | Description |
| :--- | :--- | :--- |
| **id** | `BigInt` (PK) | Incremental ID. |
| **user_id** | `UUID` (FK -> users.id) | Token owner. `ON DELETE CASCADE`. |
| **token** | `String` (Unique, Index) | Refresh token body. |
| **expires_at** | `DateTime` | Expiration date. |
| **created_at** | `DateTime` | Issuance date. |

### Indexes for `refresh_tokens`:
- `idx_token` - Index on field `token` (for fast search during refresh).
- `idx_user_id` - Index on field `user_id` (for logging out from all devices).
- `idx_expires_at` - Index on field `expires_at` (for cleaning up expired tokens via background task).
