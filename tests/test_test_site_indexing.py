"""Temporary server indexing policy applies to normal and error responses."""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings


@override_settings(TEST_SITE_NOINDEX=True)
def test_noindex_header_on_errors():
    from system.middleware import TestSiteIndexingMiddleware

    response = TestSiteIndexingMiddleware(lambda request: HttpResponse(status=403))(RequestFactory().get("/"))
    assert response["X-Robots-Tag"] == "noindex, nofollow, noarchive"


@pytest.mark.django_db
@override_settings(TEST_SITE_NOINDEX=True)
def test_test_site_robots_and_public_page(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "Disallow: /" in response.content.decode()
    assert "Sitemap:" not in response.content.decode()
    assert response["X-Robots-Tag"] == "noindex, nofollow, noarchive"
    page = client.get("/ru/")
    assert page.status_code == 200
    assert page["X-Robots-Tag"] == "noindex, nofollow, noarchive"
    assert '<meta name="robots" content="noindex, nofollow, noarchive">' in page.content.decode()
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 404
    assert sitemap["X-Robots-Tag"] == "noindex, nofollow, noarchive"


@override_settings(TEST_SITE_NOINDEX=False)
def test_normal_site_is_not_globally_noindexed(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "X-Robots-Tag" not in response
    assert "Disallow: /\n" not in response.content.decode()


@pytest.mark.django_db
@override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
def test_container_health_probe_with_proxy_header_does_not_redirect(client):
    response = client.get("/health/", HTTP_X_FORWARDED_PROTO="https")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
