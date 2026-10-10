from typing import ClassVar

from codex_django.system.mixins import AbstractUserProfile


class UserProfile(AbstractUserProfile):
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        ordering: ClassVar[list[str]] = ["-created_at"]

    def __str__(self) -> str:
        return self.get_full_name() or f"Profile #{self.pk}"
