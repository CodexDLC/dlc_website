# 🗄️ Database Schema (Media)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

The data schema separates physical file storage (CAS) and user metadata.

## Table `files` (Physical Storage)

Implements **CAS (Content Addressable Storage)**. Stores information about physical files on disk. Deduplication happens at this level.

| Field | Type | Description |
| :--- | :--- | :--- |
| **hash** | `Char(64)` (PK) | **SHA-256** hash of file content. Acts as a unique identifier. |
| **size_bytes** | `Int` | File size in bytes. |
| **mime_type** | `String` | Content MIME-type (e.g., `image/png`). |
| **path** | `String` | Relative path to storage folder (sharding). Both original and thumbnail reside here. |
| **ref_count** | `Int` | Reference counter (how many images link to this file). Used for Garbage Collection. Default: 0. |
| **created_at** | `DateTime` | Date when the file was first uploaded to the system. |

## Table `images` (User Assets)

Links a user and a physical file. Allows different users to have "their own" copies of the same file (virtually).

| Field | Type | Description |
| :--- | :--- | :--- |
| **id** | `UUID` (PK) | Unique image ID in the system (used in URLs). |
| **user_id** | `UUID` (FK) | Image owner. Link to `users` table. `ON DELETE CASCADE`. |
| **file_hash** | `Char(64)` (FK) | Link to physical file (`files.hash`). `ON DELETE RESTRICT` (cannot delete file while links exist). |
| **filename** | `String` | Original filename upon upload (e.g., "cat.png"). |
| **created_at** | `DateTime` | Date image was added to user's album. |
