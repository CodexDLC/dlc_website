from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from system.models import UserProfile
from system.selectors.client_profile import ClientProfileSelector

User = get_user_model()


@dataclass(frozen=True)
class ClientProfilePayload:
    first_name: str
    last_name: str
    patronymic: str
    phone: str
    email: str
    birth_date: str


class ClientProfileService:
    @staticmethod
    def get_profile_payload(user: User) -> tuple[UserProfile, ClientProfilePayload]:
        profile = ClientProfileSelector.get_or_create_profile(user)
        payload = ClientProfilePayload(
            first_name=profile.first_name or user.first_name or "",
            last_name=profile.last_name or user.last_name or "",
            patronymic=profile.patronymic or "",
            phone=profile.phone or "",
            email=user.email or "",
            birth_date=profile.birth_date.isoformat() if profile.birth_date else "",
        )
        return profile, payload

    @staticmethod
    def save_profile(user: User, form_data: dict[str, str]) -> tuple[bool, str]:
        profile = ClientProfileSelector.get_or_create_profile(user)

        user.first_name = form_data.get("first_name", "").strip()
        user.last_name = form_data.get("last_name", "").strip()
        user.email = form_data.get("email", "").strip()

        profile.first_name = user.first_name
        profile.last_name = user.last_name
        profile.patronymic = form_data.get("patronymic", "").strip()
        profile.phone = form_data.get("phone", "").strip()

        raw_birth_date = form_data.get("birth_date", "").strip()
        if raw_birth_date:
            try:
                profile.birth_date = datetime.strptime(raw_birth_date, "%Y-%m-%d").date()
            except ValueError:
                return False, str(_("Date of birth must use the YYYY-MM-DD format."))
        else:
            profile.birth_date = None

        user.save(update_fields=["first_name", "last_name", "email"])
        profile.save(update_fields=["first_name", "last_name", "patronymic", "phone", "birth_date"])
        return True, str(_("Profile updated successfully."))
