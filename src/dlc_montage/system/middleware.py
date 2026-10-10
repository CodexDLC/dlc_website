"""HTTP indexing policy for temporary, non-public deployments."""

from django.conf import settings


class TestSiteIndexingMiddleware:
    """Mark all Django responses, including redirects and errors, as non-indexable."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.TEST_SITE_NOINDEX:
            response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response
