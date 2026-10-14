"""Read-only Nextcloud source adapter for persistent site photo imports."""

from pathlib import PurePosixPath

from .services import ALLOWED_IMAGE_EXTENSIONS, get_site_folder_path


def list_site_photos(site, client):
    """List direct children of this site's Fotos folder; reject hostile paths."""
    folder = f"{get_site_folder_path(site, client=client).strip('/')}/Fotos"
    if any(part in {".", ".."} for part in folder.split("/")) or "\\" in folder:
        raise ValueError("Invalid site photo folder")
    photos = []
    for item in client.list_folder(folder):
        if item.get("is_directory"):
            continue
        name = item.get("name", "")
        if (
            not isinstance(name, str)
            or not name
            or len(name) > 255
            or "/" in name
            or "\\" in name
            or any(ord(character) < 32 for character in name)
            or PurePosixPath(name).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS
        ):
            continue
        canonical_path = f"{folder}/{name}"
        if len(canonical_path) > 1500 or item.get("relative_path", canonical_path) != canonical_path:
            continue
        photos.append(
            {
                "name": name,
                "path": canonical_path,
                "etag": str(item.get("etag") or "")[:255],
                "modified": str(item.get("modified") or "")[:255],
            }
        )
    return photos
