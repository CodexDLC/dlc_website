from pathlib import Path

import pytest
from httpx import AsyncClient

# --- Fixtures ---


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """
    Создает валидный 1x1 PNG файл для тестов.
    """
    # 1x1 red pixel PNG
    data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00"
        b"IEND\xaeB`\x82"
    )

    file_path = tmp_path / "test_image.png"
    file_path.write_bytes(data)
    return file_path


@pytest.fixture
def fake_exe_file(tmp_path: Path) -> Path:
    """
    Создает текстовый файл, который притворяется картинкой.
    """
    file_path = tmp_path / "virus.exe.jpg"
    file_path.write_text("MZ This is not a real image")
    return file_path


# --- Tests ---


@pytest.mark.asyncio
async def test_media_upload_flow(
    async_client: AsyncClient, sample_image: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test full media flow: Upload -> Feed -> Deduplication -> Delete
    """

    # 0. Setup: Override UPLOAD_DIR to use tmp_path
    from backend.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")

    # 1. Auth (Register & Login)
    email = "media_user@example.com"
    password = "password123"
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_res = await async_client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload Image
    with open(sample_image, "rb") as f:
        files = {"file": ("my_cat.png", f, "image/png")}
        response = await async_client.post("/api/v1/media/upload", files=files, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert "url" in data
    image_id_1 = data["id"]

    file_hash = data["file"]["hash"]

    # 3. Verify Feed
    response = await async_client.get("/api/v1/media/feed")
    assert response.status_code == 200
    feed = response.json()
    assert len(feed) > 0
    assert feed[0]["id"] == image_id_1

    # 4. Upload Duplicate (Deduplication Test)
    with open(sample_image, "rb") as f:
        files = {"file": ("my_cat_copy.png", f, "image/png")}
        response = await async_client.post("/api/v1/media/upload", files=files, headers=headers)

    assert response.status_code in [200, 201]
    data_2 = response.json()
    image_id_2 = data_2["id"]

    assert image_id_1 != image_id_2  # Different Image IDs (links)
    assert data_2["file"]["hash"] == file_hash  # Same File Hash

    # 5. Delete First Image (File should remain)
    response = await async_client.delete(f"/api/v1/media/{image_id_1}", headers=headers)
    assert response.status_code in [200, 204]

    # Check if file still exists on disk (mocked check via API or assumption)
    response = await async_client.get("/api/v1/media/feed")
    feed = response.json()
    # Should still contain the second image
    assert any(img["id"] == image_id_2 for img in feed)

    # 6. Delete Second Image (File should be GC'd)
    response = await async_client.delete(f"/api/v1/media/{image_id_2}", headers=headers)
    assert response.status_code in [200, 204]


@pytest.mark.asyncio
async def test_upload_invalid_file_type(
    async_client: AsyncClient, fake_exe_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test uploading a file with invalid magic bytes (e.g. text file renamed to .jpg).
    """
    from backend.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")

    # Auth
    email = "hacker@example.com"
    password = "password123"
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_res = await async_client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload Fake Image
    with open(fake_exe_file, "rb") as f:
        files = {"file": ("virus.jpg", f, "image/jpeg")}
        response = await async_client.post("/api/v1/media/upload", files=files, headers=headers)

    # Should fail validation
    assert response.status_code == 422  # Validation Error


@pytest.mark.asyncio
async def test_upload_too_large_file(
    async_client: AsyncClient, sample_image: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test uploading a file larger than MAX_UPLOAD_SIZE.
    """
    from backend.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")
    # Set limit to 10 bytes for this test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 10)

    # Auth
    email = "heavy_user@example.com"
    password = "password123"
    await async_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_res = await async_client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload Normal Image (which is > 10 bytes)
    with open(sample_image, "rb") as f:
        files = {"file": ("big.png", f, "image/png")}
        response = await async_client.post("/api/v1/media/upload", files=files, headers=headers)

    # Should fail validation
    assert response.status_code == 422  # Validation Error


@pytest.mark.asyncio
async def test_delete_other_user_image(
    async_client: AsyncClient, sample_image: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Test that User B cannot delete User A's image.
    """
    from backend.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path / "uploads")

    # 1. Register User A
    await async_client.post("/api/v1/auth/register", json={"email": "user_a@example.com", "password": "password123"})
    res_a = await async_client.post(
        "/api/v1/auth/login", data={"username": "user_a@example.com", "password": "password123"}
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    await async_client.post("/api/v1/auth/register", json={"email": "user_b@example.com", "password": "password123"})
    res_b = await async_client.post(
        "/api/v1/auth/login", data={"username": "user_b@example.com", "password": "password123"}
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A uploads image
    with open(sample_image, "rb") as f:
        files = {"file": ("private.png", f, "image/png")}
        response = await async_client.post("/api/v1/media/upload", files=files, headers=headers_a)

    image_id = response.json()["id"]

    # 4. User B tries to delete it
    response = await async_client.delete(f"/api/v1/media/{image_id}", headers=headers_b)

    # Should be Forbidden
    assert response.status_code == 403
