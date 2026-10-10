"""Сервисные функции интеграции с Nextcloud для создания структуры папок и сводки фото."""

from hashlib import sha256
from typing import Any

from django.core.cache import cache
from loguru import logger

from .client import NextcloudWebDAVClient


import re


def _normalize_text(text: str) -> str:
    return text.lower().replace("ß", "ss").replace("straße", "str").replace("strasse", "str")


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+[a-zA-Z]?\b", text))


def find_matching_group_folder(group, client: NextcloudWebDAVClient | None = None) -> str | None:
    """Найти существующую папку группы в Nextcloud (например, 'Thurgauer Straße 46, 50, 56')."""
    if client is None:
        client = NextcloudWebDAVClient()
    try:
        items = client.list_folder("DLC Montage/AC")
        group_name = (group.name or "").strip()
        target_nums = _extract_numbers(group_name)
        norm_target = _normalize_text(group_name)

        best_match = None
        max_common = 0
        for item in items:
            if not item.get("is_directory"):
                continue
            name = item.get("name", "")
            if name.startswith("_") or "Muster" in name:
                continue
            if name == group_name:
                return f"DLC Montage/AC/{name}"

            common = target_nums.intersection(_extract_numbers(name))
            if common and len(common) > max_common:
                max_common = len(common)
                best_match = name

        if best_match:
            return f"DLC Montage/AC/{best_match}"
    except Exception as exc:
        logger.debug("Group matching check failed: {}", exc)
    return None


def find_matching_site_folder(site, client: NextcloudWebDAVClient | None = None) -> str | None:
    """Найти существующую папку объекта внутри папки группы (например, '2026-1511 Thurgauer Straße 46')."""
    if client is None:
        client = NextcloudWebDAVClient()
    group_path = get_group_folder_path(site.group, client=client) if site.group else "DLC Montage/AC"
    try:
        items = client.list_folder(group_path)
        site_name = (site.name or "").strip()
        p_num = (site.project_number or "").strip()
        site_nums = _extract_numbers(site_name)

        for item in items:
            if not item.get("is_directory"):
                continue
            name = item.get("name", "")
            # 1. Точное совпадение по номеру проекта
            if p_num and p_num in name:
                return f"{group_path}/{name}"
            # 2. Совпадение по номеру дома объекта
            if site_nums and site_nums.intersection(_extract_numbers(name)):
                return f"{group_path}/{name}"
    except Exception as exc:
        logger.debug("Site matching check failed: {}", exc)
    return None


def get_site_folder_name(site) -> str:
    """Сформировать стандартное имя папки объекта (Standort)."""
    p_num = (site.project_number or "").strip()
    name = (site.name or "").strip()
    addr = (site.address or "").strip()

    if p_num and name:
        return f"{p_num} - {name}"
    if p_num and addr:
        return f"{p_num} - {addr}"
    return name or addr or f"Standort_{site.pk}"


def get_group_folder_path(group, client: NextcloudWebDAVClient | None = None) -> str:
    """Сформировать путь папки группы проектов (Anlage) в Nextcloud, учитывая существующую."""
    matched = find_matching_group_folder(group, client=client)
    if matched:
        return matched
    group_name = (group.name or f"Group_{group.pk}").strip()
    return f"DLC Montage/AC/{group_name}"


def get_site_folder_path(site, client: NextcloudWebDAVClient | None = None) -> str:
    """Сформировать полный относительный путь к папке объекта в Nextcloud, учитывая существующую."""
    matched = find_matching_site_folder(site, client=client)
    if matched:
        return matched
    folder_name = get_site_folder_name(site)
    if site.group:
        group_path = get_group_folder_path(site.group, client=client)
        return f"{group_path}/{folder_name}"
    return f"DLC Montage/AC/{folder_name}"


def ensure_group_folders(group, client: NextcloudWebDAVClient | None = None) -> bool:
    """Создать структуру папки группы в Nextcloud (идемпотентно и не дублируя существующие)."""
    if client is None:
        client = NextcloudWebDAVClient()
    group_path = get_group_folder_path(group, client=client)
    try:
        logger.info("Ensuring Nextcloud folder for group {}: '{}'", group.pk, group_path)
        return client.ensure_folder(group_path)
    except Exception as exc:
        logger.warning("Failed to ensure Nextcloud group folder '{}': {}", group_path, exc)
        return False


def ensure_site_folders(site, client: NextcloudWebDAVClient | None = None) -> bool:
    """Создать структуру папок объекта (Standort, Dokumente, Fotos) в Nextcloud без дублирования."""
    if client is None:
        client = NextcloudWebDAVClient()
    site_path = get_site_folder_path(site, client=client)
    try:
        logger.info("Ensuring Nextcloud folders for site {}: '{}'", site.pk, site_path)
        doc_path = f"{site_path}/Dokumente"
        photo_path = f"{site_path}/Fotos"
        ok_doc = client.ensure_folder(doc_path)
        ok_photo = client.ensure_folder(photo_path)
        return ok_doc and ok_photo
    except Exception as exc:
        logger.warning("Failed to ensure Nextcloud site folders for '{}': {}", site_path, exc)
        return False


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALL_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def validate_image_bytes(data: bytes, ext: str) -> str:
    """Проверить сигнатуру байтов изображения и вернуть безопасный MIME-тип.

    Категорически блокирует HTML, XML, SVG и нерастровые/неподдерживаемые файлы.
    """
    if not data:
        raise ValueError("Empty image content.")

    # Защита от полиглотов, XSS и внедрения HTML/SVG
    header_chunk = data[:1024].lstrip()
    if header_chunk.startswith((b"<html", b"<!DOCTYPE", b"<!doctype", b"<?xml", b"<svg")):
        raise ValueError("Content is HTML or XML/SVG; rejected for safe image proxy.")

    ext_clean = ext.lower()
    if ext_clean in (".jpg", ".jpeg"):
        if not data.startswith(b"\xff\xd8\xff"):
            raise ValueError("Invalid JPEG magic bytes.")
        return "image/jpeg"
    elif ext_clean == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Invalid PNG magic bytes.")
        return "image/png"
    elif ext_clean == ".webp":
        if not (data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP"):
            raise ValueError("Invalid WebP magic bytes.")
        return "image/webp"
    else:
        raise ValueError(f"Unsupported image format: '{ext_clean}'")


def get_site_photo_cache_key(site) -> str:
    """Сформировать ключ кеша сводки фото с привязкой к id объекта и текущему каноническому пути."""
    canonical_folder = f"{get_site_folder_path(site)}/Fotos"
    folder_digest = sha256(canonical_folder.encode("utf-8")).hexdigest()
    return f"nextcloud_photos:{site.pk}:{folder_digest}"


def get_site_photo_summary(site, client: NextcloudWebDAVClient | None = None) -> dict[str, Any]:
    """Получить сводку фотофиксации объекта из Nextcloud с кешированием на 15 минут.

    Явно различает статус успешного ответа ('ok') и недоступности хранилища ('unavailable').
    """
    cache_key = get_site_photo_cache_key(site)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    site_path = get_site_folder_path(site)
    photo_path = f"{site_path}/Fotos"
    if client is None:
        client = NextcloudWebDAVClient()

    if not client.is_configured:
        return {
            "status": "unavailable",
            "is_available": False,
            "has_photos": False,
            "count": 0,
            "folder_path": photo_path,
            "photos": [],
            "error": "Nextcloud photo storage is not configured.",
        }

    try:
        items = client.list_folder(photo_path)
        photos = []
        for item in items:
            if item.get("is_directory"):
                continue
            name = item.get("name", "")
            ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
            if ext in ALL_PHOTO_EXTENSIONS:
                photos.append({
                    "name": name,
                    "relative_path": item.get("relative_path", f"{photo_path}/{name}"),
                    "is_directory": False,
                    "is_previewable": ext in ALLOWED_IMAGE_EXTENSIONS,
                    "extension": ext,
                })

        summary = {
            "status": "ok",
            "is_available": True,
            "has_photos": len(photos) > 0,
            "count": len(photos),
            "folder_path": photo_path,
            "photos": photos,
            "error": None,
        }
        cache.set(cache_key, summary, timeout=900)
        return summary
    except Exception as exc:
        logger.warning("Failed to get photo summary for site {}: {}", site.pk, exc)
        return {
            "status": "unavailable",
            "is_available": False,
            "has_photos": False,
            "count": 0,
            "folder_path": photo_path,
            "photos": [],
            "error": str(exc),
        }


def fetch_site_photo(
    site,
    filename: str,
    client: NextcloudWebDAVClient | None = None,
) -> tuple[bytes, str]:
    """Безопасно получить байты и MIME-тип фотографии конкретного объекта.

    Проверяет путь строго по белому списку из списка фото папки Fotos/ этого объекта.
    Никогда не обращается к произвольным URL или файлам других объектов.
    """
    import re

    clean_filename = filename.strip()
    if not clean_filename or "/" in clean_filename or "\\" in clean_filename or ".." in clean_filename:
        raise ValueError(f"Invalid photo filename: '{filename}'")

    if not re.match(r"^[\w\-. ]+$", clean_filename):
        raise ValueError(f"Filename contains illegal characters: '{filename}'")

    ext = ("." + clean_filename.rsplit(".", 1)[-1].lower()) if "." in clean_filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"Format '{ext}' is not supported for safe browser preview.")

    summary = get_site_photo_summary(site, client=client)
    if not summary.get("is_available"):
        from .client import NextcloudWebDAVError

        raise NextcloudWebDAVError("Nextcloud photo storage is currently unavailable.")

    # Проверка, что файл действительно присутствует в листинге Fotos этого объекта
    allowed_photos = {p["name"]: p for p in summary.get("photos", []) if p.get("is_previewable")}
    if clean_filename not in allowed_photos:
        raise FileNotFoundError(f"Photo '{clean_filename}' is not listed in site photos.")

    if client is None:
        client = NextcloudWebDAVClient()

    folder_path = f"{get_site_folder_path(site)}/Fotos"
    photo_rel_path = f"{folder_path}/{clean_filename}"

    data, _ct = client.get_file(photo_rel_path)
    safe_mime = validate_image_bytes(data, ext)
    return data, safe_mime
