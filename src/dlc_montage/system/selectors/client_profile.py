from __future__ import annotations

from django.contrib.auth import get_user_model
from system.models import UserProfile

User = get_user_model()


class ClientProfileSelector:
    @staticmethod
    def get_or_create_profile(user: User) -> UserProfile:
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "source": "manual",
            },
        )
        return profile
