from typing import Any, ClassVar

from codex_django.system.mixins.seo import AbstractStaticPageSeo
from django.db import models
from django.utils.translation import gettext_lazy as _


class StaticPageSeo(AbstractStaticPageSeo):
    """
    SEO settings for specific static pages of the project.
    """

    KEY_HOME = "home"
    KEY_CONTACTS = "contacts"
    KEY_IMPRESSUM = "impressum"
    KEY_DATENSCHUTZ = "datenschutz"

    PAGE_CHOICES: ClassVar[list] = [
        (KEY_HOME, _("Главная страница")),
        (KEY_CONTACTS, _("Контакты")),
        (KEY_IMPRESSUM, _("Impressum")),
        (KEY_DATENSCHUTZ, _("Datenschutz")),
    ]

    page_key: Any = models.CharField(
        max_length=50,
        choices=PAGE_CHOICES,
        unique=True,
        verbose_name=_("ID Страницы"),
    )

    class Meta:
        verbose_name = _("SEO статичной страницы")
        verbose_name_plural = _("SEO статичных страниц")

    def __str__(self):
        return self.get_page_key_display()
