# 🔌 API Layer (Routers)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../../../README.md)

Media domain endpoints.

## Endpoints

### `POST /media/upload`
*   **Auth:** Required (`Bearer Token`).
*   **Input:** `Multipart/Form-Data`.
    *   `file`: Binary data.
*   **Action:** Calls `MediaService.upload_image`.
*   **Response:** `201 Created` + JSON with image ID and links.

### `GET /media/feed`
*   **Auth:** Not required (public access).
*   **Input:** Query params:
    *   `limit` (default: 20)
    *   `offset` (default: 0)
*   **Action:** Calls `MediaService.get_public_feed`.
*   **Response:** `200 OK` + List of "light" objects (thumbnails only).

### `GET /media/{image_id}`
*   **Auth:** Not required.
*   **Input:** Path param `image_id` (UUID).
*   **Action:** Calls `MediaService.get_image_details`.
*   **Response:** `200 OK` + Full object (original + info).

### `DELETE /media/{image_id}`
*   **Auth:** Required (`Bearer Token`).
*   **Input:** Path param `image_id` (UUID).
*   **Action:** Calls `MediaService.delete_image`.
*   **Response:** `204 No Content`.
