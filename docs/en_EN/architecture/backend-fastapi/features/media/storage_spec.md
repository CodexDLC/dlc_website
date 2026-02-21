# 💾 Spec: Media Storage & Validation (CAS)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

**Domain:** `apps.media`
**Layer:** Service Layer (Business Logic)
**Status:** Implemented

## 1. Concept: Content-Addressable Storage (CAS)

We refuse to store files by name (`cat.png`). Instead, we use the CAS approach: the file address is determined by its content.

*   **Hashing Algorithm:** SHA-256.
*   **Guarantee:** Identical files = One physical file on disk (Deduplication).
*   **Security:** Filename on disk does not depend on user input.

## 2. File System Structure (Sharding)

To avoid the "million files in one folder" problem, we use two-level sharding based on hash.

**Example:**
*   File: `cat.png`
*   SHA-256: `a1b2c3d4...`
*   Storage Path: `media/storage/a1/b2/a1b2c3d4...` (no extension)
*   Thumbnail Path: `media/storage/a1/b2/a1b2c3d4..._thumb.jpg`

**Path Formula:**
```python
root / hash[0:2] / hash[2:4] / hash
```

## 3. Upload Flow

This process is implemented in `MediaService`.

### Step A: Validation (Security First)
1.  **Size Check:** We count bytes while reading the stream. If size exceeds `MAX_UPLOAD_SIZE` (from config), upload is aborted, temp file deleted.
2.  **Magic Bytes Check:** (Planned) Use `python-magic` to verify real file type.

### Step B: Hashing and Deduplication
We read file in chunks (64KB), feeding them to `hashlib.sha256()`.
Simultaneously writing data to temp file: `media/temp/upload_UUID.tmp`.

**DB Check:** Query DB: `SELECT hash FROM files WHERE hash = :new_hash LIMIT 1`

*   **HIT (Exists in DB):**
    *   Do NOT save physical file (it already exists).
    *   Delete temp file.
    *   Create new record in `images` table (link: New User -> Old Hash).
    *   Increment `ref_count` of the file.
    *   Return success.
*   **MISS (Not in DB):**
    *   Proceed to Step C.

### Step C: Physical Save (Atomic Write)
If we save file directly and server crashes in the middle — we get a corrupted file. We use **Atomic Save** pattern:

1.  Data is already written to temp file `media/temp/upload_UUID.tmp` (at Step B).
2.  Perform `shutil.move()` to target folder `media/storage/a1/b2/....`.
3.  **Thumbnail Generation:** Create `_thumb.jpg` (300px) next to original.

**IMPORTANT:** `shutil.move()` and `PIL` are used in a separate thread (`run_in_threadpool`) to avoid blocking the Event Loop.

## 4. Data Schema (Database Model)

We need to separate the concept of "User Image" and "Physical Blob".

### Table `files` (Blob Storage)
Stores info about physical files.
*   `hash` (PK, CHAR(64))
*   `size_bytes` (INT)
*   `mime_type` (VARCHAR)
*   `created_at` (DATETIME)
*   `ref_count` (INT) — reference counter (for garbage collector).

### Table `images` (User Assets)
What the user sees.
*   `id` (PK, UUID)
*   `user_id` (FK -> Users)
*   `file_hash` (FK -> files.hash)
*   `filename` (VARCHAR) — original name ("my_cat.png")
