from codex_django.system.mixins import AbstractStaticTranslation
from django.utils.translation import gettext_lazy as _


class StaticTranslation(AbstractStaticTranslation):
    """
    Concrete model for static page content/translations.
    Used by context_processor to provide content in templates.
    """

    class Meta(AbstractStaticTranslation.Meta):
        verbose_name = _("Статический перевод")
        verbose_name_plural = _("Статические переводы")
