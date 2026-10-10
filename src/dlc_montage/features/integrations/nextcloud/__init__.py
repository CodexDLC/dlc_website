"""Интеграция с корпоративным хранилищем Nextcloud MBG по WebDAV."""

from .client import NextcloudWebDAVClient
from .services import (
    ensure_group_folders,
    ensure_site_folders,
    get_group_folder_path,
    get_site_folder_name,
    get_site_folder_path,
    get_site_photo_summary,
)

__all__ = [
    "NextcloudWebDAVClient",
    "ensure_group_folders",
    "ensure_site_folders",
    "get_group_folder_path",
    "get_site_folder_name",
    "get_site_folder_path",
    "get_site_photo_summary",
]
