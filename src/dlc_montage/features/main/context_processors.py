"""Shared public copy for pages and their error templates."""

from django.conf import settings
from django.utils.translation import get_language

from .selectors import get_public_copy


def public_site_content(request):
    """Expose only public text definitions; no database reads or mutations."""
    return {"public_copy": get_public_copy(get_language() or settings.LANGUAGE_CODE)}
