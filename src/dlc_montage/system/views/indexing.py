"""Crawler instructions follow the selected deployment environment."""

from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from django.http import Http404, HttpResponse


def robots_txt(request):
    """Discourage crawling on a test domain and advertise only the configured sitemap."""
    if settings.TEST_SITE_NOINDEX:
        content = "User-agent: *\nDisallow: /\n"
    else:
        content = "User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /api/\n"
        content += f"\nSitemap: {settings.SITE_BASE_URL.rstrip('/')}/sitemap.xml\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def site_sitemap(request, **kwargs):
    """Do not publish a sitemap for the temporary test site."""
    if settings.TEST_SITE_NOINDEX:
        raise Http404
    return sitemap(request, **kwargs)
