"""Language switching for localized pages without depending on a previous cookie."""

from urllib.parse import urlsplit

from django.conf import settings
from django.utils.translation import override
from django.views.decorators.http import require_POST
from django.views.i18n import set_language


@require_POST
def switch_language(request):
    """Use the page language while retaining Django's redirect and cookie checks."""
    try:
        source = urlsplit(request.POST.get("next", "")).path.strip("/").split("/", 1)[0]
    except ValueError:
        return set_language(request)
    languages = {code for code, _name in settings.LANGUAGES}
    if source in languages:
        with override(source):
            return set_language(request)
    return set_language(request)
