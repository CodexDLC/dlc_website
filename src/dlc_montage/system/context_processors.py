"""Environment-specific presentation flags."""

from django.conf import settings


def deployment(request):
    """Expose only the indexing flag, never deployment credentials."""
    return {"TEST_SITE_NOINDEX": settings.TEST_SITE_NOINDEX}
