from __future__ import annotations

from typing import TYPE_CHECKING

from codex_django.cabinet.types import CardGridData, CardItem
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.db.models import QuerySet


class UserSelector:
    @staticmethod
    def get_users_queryset(segment: str | None = None) -> QuerySet:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        qs = User.objects.select_related("profile").all()

        if segment == "clients":
            qs = qs.filter(profile__source__gt="")
        elif segment == "staff":
            qs = qs.filter(is_staff=True)

        return qs

    @classmethod
    def get_users_grid(cls, segment: str | None = None) -> CardGridData:
        queryset = cls.get_users_queryset(segment)
        items = []

        for user in queryset:
            profile = getattr(user, "profile", None)
            if profile:
                full_name = profile.get_full_name() or user.get_full_name() or user.username
                avatar = profile.get_initials()
            else:
                full_name = user.get_full_name() or user.username
                avatar = user.username[0].upper() if user.username else "?"

            subtitle = user.email
            meta = []
            if profile:
                if profile.phone:
                    meta.append(("bi-phone", profile.phone))
                if profile.source:
                    meta.append(("bi-box-arrow-in-right", f"{_('Source')}: {profile.source}"))
            if user.is_staff:
                meta.append(("bi-shield-check", _("Staff Member")))

            items.append(
                CardItem(
                    id=str(user.pk),
                    title=full_name,
                    subtitle=subtitle,
                    avatar=avatar,
                    badge=profile.source.capitalize() if profile and profile.source else "",
                    badge_style="secondary",
                    url="#",
                    meta=meta,
                )
            )

        return CardGridData(
            items=items,
            search_placeholder=_("Search users..."),
            empty_message=_("No users found"),
        )
