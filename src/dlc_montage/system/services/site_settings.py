from __future__ import annotations

from typing import TYPE_CHECKING, Any

from codex_django.cabinet.services.site_settings import SiteSettingsService as LibrarySiteSettingsService

if TYPE_CHECKING:
    from django.http import HttpRequest


class SiteSettingsService(LibrarySiteSettingsService):
    @staticmethod
    def save_context(request: HttpRequest) -> tuple[bool, str]:
        return LibrarySiteSettingsService.save_context(request)  # type: ignore[no-any-return]

    @staticmethod
    def get_context(request: HttpRequest) -> dict[str, Any]:
        return LibrarySiteSettingsService.get_context(request)  # type: ignore[no-any-return]
