# 🧪 Testing Strategy: Media Feature

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

## 🎯 Philosophy and Goals

**Main Goal:** Guarantee data integrity (files) and correct deduplication (CAS).

**Principles:**
1.  **Data Integrity:** File on disk must match record in DB.
2.  **Cleanup:** User deletion of an image must be handled correctly (delete file only if no one else uses it).
3.  **Mock Storage:** In unit tests, do not write to real disk, use `io.BytesIO` or `aiofiles` mocks.

## 📊 Testing Pyramid

### 1. Unit Tests (Services)
Isolated verification of `MediaService` logic.
*   **Scope:** Hash calculation, deduplication logic, access rights check.
*   **Mocking:** `IMediaRepository`, file system (`aiofiles`, `os`).
*   **Location:** `src/backend-fastapi/features/media/tests/unit/`

### 2. Integration Tests (API)
Verification of upload and download using temporary folder (`tmp_path`).
*   **Scope:** `MediaRouter`.
*   **Focus:** Upload multipart/form-data, Serving static files (if via API), deletion.
*   **Location:** `src/backend-fastapi/features/media/tests/integration/`

---

## 🧪 Unit Testing Specifications

### `MediaService`
**File:** `src/backend-fastapi/features/media/tests/unit/test_media_service.py`

**Scenarios:**
*   **Upload (New File):**
    *   Input: `UploadFile` (stream).
    *   Expectation: Hash calculated, `shutil.move` called (mock), `repo.create_file` and `repo.create_image` called.
*   **Upload (Deduplication):**
    *   Input: File whose hash already exists in repo mock (`get_file_by_hash` returns object).
    *   Expectation: `shutil.move` NOT called, only `repo.create_image` called.
*   **Delete (Owner):**
    *   Input: `user_id` matches image owner.
    *   Expectation: `repo.delete_image` called.
*   **Delete (Not Owner):**
    *   Input: `user_id` is alien.
    *   Expectation: `PermissionDeniedException`.

---

## 🔗 Integration Testing Specifications

### `Upload & Gallery Flow`
**File:** `src/backend-fastapi/features/media/tests/integration/test_media_flow.py`

**Goal:** Verify upload, display, and deletion.

**Test Steps:**
1.  **Upload:** POST `/media/upload` (file `cat.jpg`) -> 200 OK + JSON (url).
2.  **Verify Storage:** Check that file physically appeared in test folder `uploads/storage/...`.
3.  **Feed:** GET `/media/feed` -> List contains our image.
4.  **Upload Duplicate:** Upload same `cat.jpg` again -> 200 OK.
    *   Check that file on disk is ONE (deduplication worked).
    *   In DB two `images` records link to one `file`.
5.  **Delete 1:** Delete first image.
    *   File on disk must REMAIN (as second link exists).
6.  **Delete 2:** Delete second image.
    *   File on disk must DISAPPEAR (ref count = 0).

---

## 🛠️ Fixtures & Mocks

*   `mock_media_repo`: Async mock of repository.
*   `temp_storage_dir`: `pytest` fixture creating temp folder for tests and cleaning it up.
*   `sample_image_file`: Byte stream of real valid image (1x1 pixel) for tests.
