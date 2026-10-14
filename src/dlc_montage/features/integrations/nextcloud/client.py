"""Низкоуровневый клиент WebDAV для работы с хранилищем Nextcloud MBG."""

from time import monotonic
from typing import Any
from urllib.parse import quote, unquote

import defusedxml.ElementTree as ET
import requests
from django.conf import settings
from loguru import logger


class NextcloudWebDAVError(Exception):
    """Базовое исключение сетевых операций WebDAV."""


class NextcloudWebDAVClient:
    """Адаптер протокола WebDAV для взаимодействия с Nextcloud."""

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 15,
    ) -> None:
        raw_url = base_url if base_url is not None else getattr(settings, "NEXTCLOUD_WEBDAV_URL", "")
        self.base_url = (raw_url.rstrip("/") + "/") if raw_url else ""
        self.username = username if username is not None else getattr(settings, "NEXTCLOUD_USER", "")
        self.password = password if password is not None else getattr(settings, "NEXTCLOUD_PASSWORD", "")
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """True if all connection settings are present."""
        return bool(self.base_url and self.username and self.password)

    @property
    def auth(self) -> tuple[str, str] | None:
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def _full_url(self, relative_path: str, is_collection: bool = True) -> str:
        clean = relative_path.strip("/")
        if not clean:
            return self.base_url
        encoded = quote(clean, safe="/")
        if is_collection:
            return f"{self.base_url}{encoded}/"
        return f"{self.base_url}{encoded}"

    def ensure_folder(self, relative_path: str) -> bool:
        """Рекурсивно создать папку по WebDAV (MKCOL).

        Возвращает True, если папка создана или уже существовала.
        """
        parts = [p for p in relative_path.strip("/").split("/") if p]
        if not parts:
            return True

        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            url = self._full_url(current, is_collection=True)
            try:
                res = requests.request("MKCOL", url, auth=self.auth, timeout=self.timeout)
                # 201 = Created, 405 = Method Not Allowed (already exists)
                if res.status_code in (201, 405):
                    continue
                logger.warning(
                    "Nextcloud MKCOL unexpected status: path='{}', status={}",
                    current,
                    res.status_code,
                )
                return False
            except requests.RequestException as exc:
                logger.error(
                    "Nextcloud MKCOL network error: path='{}', error={}",
                    current,
                    str(exc),
                )
                raise NextcloudWebDAVError(f"Network error while ensuring folder {current}: {exc}") from exc

        return True

    def list_folder(self, relative_path: str, depth: str = "1") -> list[dict[str, Any]]:
        """Получить список файлов и подпапок через PROPFIND.

        Выбрасывает NextcloudWebDAVError при ошибке связи или неожиданном HTTP-статусе.
        Возвращает пустой список, если папка ещё не создана (HTTP 404).
        """
        import posixpath

        url = self._full_url(relative_path, is_collection=True)
        res = None
        try:
            res = requests.request(
                "PROPFIND",
                url,
                auth=self.auth,
                headers={"Depth": depth},
                timeout=self.timeout,
                allow_redirects=False,
            )
            is_redirect = (getattr(res, "is_redirect", False) is True) or (
                res.status_code in (301, 302, 303, 307, 308)
            )
            if is_redirect:
                logger.warning(
                    "Nextcloud PROPFIND rejected redirect: path='{}', status={}", relative_path, res.status_code
                )
                raise NextcloudWebDAVError(f"Redirect rejected for '{relative_path}': status {res.status_code}")

            if res.status_code == 404:
                logger.info("Nextcloud PROPFIND folder not found: path='{}'", relative_path)
                return []
            if res.status_code not in (200, 207):
                logger.warning(
                    "Nextcloud PROPFIND failed: path='{}', status={}",
                    relative_path,
                    res.status_code,
                )
                raise NextcloudWebDAVError(
                    f"PROPFIND failed for '{relative_path}' with HTTP status {res.status_code}"
                )

            root = ET.fromstring(res.text)
            items = []
            base_prefix = f"/remote.php/dav/files/{self.username}/" if self.username else "/remote.php/dav/files/"
            clean_expected = relative_path.strip("/")

            for resp in root.findall("{DAV:}response"):
                href_node = resp.find("{DAV:}href")
                if href_node is None or not href_node.text:
                    continue
                decoded = unquote(href_node.text)
                if decoded.startswith(base_prefix):
                    rel = decoded[len(base_prefix):]
                elif decoded.startswith("/remote.php/dav/files/"):
                    # Чужой или подозрительный href за пределами пространства пользователя
                    logger.warning("Nextcloud PROPFIND hostile or foreign href ignored: '{}'", decoded)
                    continue
                else:
                    rel = decoded

                rel = rel.rstrip("/")
                norm = posixpath.normpath(rel)
                if norm.startswith("..") or norm.startswith("/") or "/../" in rel:
                    logger.warning("Nextcloud PROPFIND traversal href ignored: '{}'", rel)
                    continue

                if not rel or rel == clean_expected:
                    continue

                if clean_expected and not rel.startswith(clean_expected + "/"):
                    logger.warning(
                        "Nextcloud PROPFIND href outside requested collection ignored: '{}'", rel
                    )
                    continue

                # Проверяем, коллекция (папка) ли это
                is_dir = False
                etag = modified = ""
                propstat = resp.find("{DAV:}propstat")
                if propstat is not None:
                    prop = propstat.find("{DAV:}prop")
                    if prop is not None:
                        etag_node = prop.find("{DAV:}getetag")
                        modified_node = prop.find("{DAV:}getlastmodified")
                        etag = (etag_node.text or "") if etag_node is not None else ""
                        modified = (modified_node.text or "") if modified_node is not None else ""
                        resourcetype = prop.find("{DAV:}resourcetype")
                        if resourcetype is not None and resourcetype.find("{DAV:}collection") is not None:
                            is_dir = True

                name = rel.split("/")[-1]
                if not name or name in {".", ".."}:
                    continue

                items.append({
                    "relative_path": rel,
                    "name": name,
                    "is_directory": is_dir,
                    "etag": etag,
                    "modified": modified,
                })

            return items
        except requests.RequestException as exc:
            logger.error(
                "Nextcloud PROPFIND error: path='{}', error={}",
                relative_path,
                str(exc),
            )
            raise NextcloudWebDAVError(f"Network error while listing {relative_path}: {exc}") from exc
        finally:
            if res is not None:
                res.close()

    def get_file(
        self, relative_path: str, max_size: int = 25 * 1024 * 1024, *, deadline_seconds: float | None = None,
    ) -> tuple[bytes, str]:
        """Безопасно скачать файл из Nextcloud без перехода по редиректам.

        Возвращает кортеж (content_bytes, content_type).
        """
        import posixpath

        clean = relative_path.strip("/")
        norm = posixpath.normpath(clean)
        if norm.startswith("..") or norm.startswith("/") or "/../" in clean:
            raise NextcloudWebDAVError(f"Invalid path traversal in file path: {relative_path}")

        url = self._full_url(clean, is_collection=False)
        deadline = monotonic() + deadline_seconds if deadline_seconds is not None else None
        res = None
        try:
            res = requests.get(
                url,
                auth=self.auth,
                timeout=self.timeout,
                allow_redirects=False,
                stream=True,
            )
            is_redirect = (getattr(res, "is_redirect", False) is True) or (
                res.status_code in (301, 302, 303, 307, 308)
            )
            if is_redirect:
                logger.warning(
                    "Nextcloud GET rejected redirect: path='{}', status={}", clean, res.status_code
                )
                raise NextcloudWebDAVError(f"Redirect rejected for '{clean}': status {res.status_code}")

            if res.status_code != 200:
                logger.warning("Nextcloud GET failed: path='{}', status={}", clean, res.status_code)
                raise NextcloudWebDAVError(f"GET failed for '{clean}': status {res.status_code}")

            cl = res.headers.get("Content-Length")
            if cl and cl.isdigit() and int(cl) > max_size:
                raise NextcloudWebDAVError(f"Payload size {cl} exceeds maximum allowed {max_size}")

            content = bytearray()
            for chunk in res.iter_content(chunk_size=65536):
                if deadline is not None and monotonic() >= deadline:
                    raise NextcloudWebDAVError("Photo download exceeded its time budget")
                content.extend(chunk)
                if len(content) > max_size:
                    raise NextcloudWebDAVError(f"Payload exceeded maximum allowed {max_size}")

            content_type = res.headers.get("Content-Type", "")
            return bytes(content), content_type
        except requests.RequestException as exc:
            logger.error("Nextcloud GET network error: path='{}', error={}", clean, exc)
            raise NextcloudWebDAVError(f"Network error while fetching {clean}: {exc}") from exc
        finally:
            if res is not None:
                res.close()
