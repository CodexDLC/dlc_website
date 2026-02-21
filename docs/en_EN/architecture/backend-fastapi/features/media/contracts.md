# 📜 Contracts (Repositories)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Interfaces for database interaction, hiding SQL/SQLAlchemy implementation.
The project uses **`typing.Protocol`** to define contracts (Duck Typing).

## `IMediaRepository`

The interface combines work with `files` and `images` tables.

### File Operations (CAS)

*   **`get_file_by_hash(file_hash: str) -> Optional[File]`**
    *   Checks for physical file existence in DB. Used for deduplication before saving to disk.
*   **`create_file(hash: str, size_bytes: int, mime_type: str, path: str) -> File`**
    *   Creates a record in `files` table (registers a new physical blob).
    *   Initial `ref_count` is set to 0.
*   **`delete_file(file_hash: str) -> None`**
    *   Deletes record from `files` table. Called by Garbage Collector when reference count is 0.
*   **`get_usage_count(file_hash: str) -> int`**
    *   Returns current `ref_count` from `files` table.

### Image Operations (User Assets)

*   **`create_image(user_id: UUID, file_hash: str, filename: str) -> Image`**
    *   Creates record in `images` table, linking user with existing file.
    *   **Side Effect:** Increments `ref_count` of the linked file.
*   **`get_image_by_id(image_id: UUID) -> Optional[Image]`**
    *   Gets full image info (owner, hash, metadata, date).
    *   Loads linked `File` (Eager Loading).
*   **`get_public_images(limit: int, offset: int) -> List[Image]`**
    *   Returns list of images for the main feed.
    *   Sorted by novelty (`created_at DESC`).
*   **`get_images_by_user(user_id: UUID, limit: int, offset: int) -> List[Image]`**
    *   Returns gallery of a specific user.
*   **`delete_image(image_id: UUID) -> None`**
    *   Deletes record from `images` table (unlinks file from user).
    *   **Side Effect:** Decrements `ref_count` of the linked file.

### Transaction Management

*   **`commit() -> None`**
    *   Commit the current transaction.
