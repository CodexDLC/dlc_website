# 🧠 Business Logic (Services)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

## `MediaService`

Orchestrator managing image upload, processing, and deletion.
Manages transactions via calling `commit()` of the repository.

### `upload_image(user_id: UUID, file: UploadFile, filename: str) -> Image`
1.  **Hashing:** Reads file stream and calculates SHA-256 hash.
2.  **Deduplication Check:** Checks file existence in DB (`repo.get_file_by_hash`).
    *   **"New File" Branch (Miss):**
        1.  Saves original to disk (Atomic Write).
        2.  Generates thumbnail via Pillow.
        3.  Saves thumbnail next to original.
        4.  Registers file in DB (`repo.create_file`).
    *   **"Duplicate" Branch (Hit):**
        1.  Skips saving to disk (file already exists).
3.  **Linking:** Creates user record (`repo.create_image`), linking `user_id` and `file_hash`.
4.  **Commit:** Commits transaction (`repo.commit`).
5.  **Return:** Returns created image object.

### `get_public_feed(limit: int, offset: int) -> List[ImageFeedSchema]`
1.  Requests image list from repository (`repo.get_public_images`).
2.  Forms response, providing link **only to thumbnail** (`_thumb.jpg`) to optimize feed loading speed.

### `get_image_details(image_id: UUID) -> ImageDetailSchema`
1.  Requests data by ID (`repo.get_image_by_id`).
    *   If not found — error `404 Not Found`.
2.  Returns full object:
    *   Link to original.
    *   Link to thumbnail.
    *   Author info.
    *   Upload date.

### `delete_image(user_id: UUID, image_id: UUID)`
1.  **Auth Check:** Checks if image belongs to user (`image.user_id == user_id`).
    *   If not — error `403 Forbidden`.
2.  **Soft Delete:** Deletes record from `images` table (`repo.delete_image`).
3.  **Garbage Collection (GC):**
    1.  Takes `file_hash` of deleted image.
    2.  Checks usage counter (`repo.get_usage_count`).
    3.  **If counter == 0:**
        *   Deletes physical original file from disk.
        *   Deletes physical thumbnail file from disk.
        *   Deletes record from `files` table (`repo.delete_file`).
4.  **Commit:** Commits transaction (`repo.commit`).
