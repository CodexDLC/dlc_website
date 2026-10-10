from __future__ import annotations

from typing import ClassVar

from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from system.selectors.users import UserSelector


class UserService:
    """Page-service contract for cabinet users pages.

    Returns:
        cards: CardGridData for ``cabinet/components/card_grid.html``
        header_title: page heading
        header_subtitle: segment-specific page title
        active_segment: current querystring segment

    Data source:
        ``system.selectors.users.UserSelector``
    """

    _SEGMENT_TITLES: ClassVar[dict[str, str]] = {
        "all": str(_("All Users")),
        "clients": str(_("Clients")),
        "staff": str(_("Staff")),
    }

    @classmethod
    def get_list_context(cls, request: HttpRequest) -> dict[str, object]:
        segment = request.GET.get("segment", "all")
        return {
            "cards": UserSelector.get_users_grid(segment=segment),
            "header_title": str(_("Administration")),
            "header_subtitle": cls._SEGMENT_TITLES.get(segment, str(_("Users"))),
            "active_segment": segment,
        }
