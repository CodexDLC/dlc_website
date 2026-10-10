"""Tests for container readiness, production config guards, and health check contracts."""

import importlib
import os
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from features.integrations.nextcloud.client import NextcloudWebDAVClient
from features.integrations.nextcloud.services import get_site_photo_summary
from features.projects.models import AcObject, ProjectGroup


class ProductionSettingsGuardsTest(SimpleTestCase):
    """Verify production settings fail closed without PostgreSQL and reject placeholders."""

    VALID_URL = "postgres://dlc_montage:test_secret@127.0.0.1:5432/dlc_montage"
    VALID_SECRET = "production-test-secret-key-with-minimum-32-characters-length"  # noqa: S105

    def test_production_rejects_missing_database_url(self):
        with patch.dict(os.environ, {"SECRET_KEY": self.VALID_SECRET}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
                import dlc_montage.core.settings.prod as prod_settings

                importlib.reload(prod_settings)

    def test_production_rejects_sqlite_database_url(self):
        with patch.dict(
            os.environ, {"DATABASE_URL": "sqlite:///tmp/test.sqlite3", "SECRET_KEY": self.VALID_SECRET}, clear=True
        ):
            with pytest.raises(ImproperlyConfigured, match="PostgreSQL"):
                import dlc_montage.core.settings.prod as prod_settings

                importlib.reload(prod_settings)

    def test_production_rejects_missing_or_insecure_secret_key(self):
        # Missing SECRET_KEY
        with patch.dict(os.environ, {"DATABASE_URL": self.VALID_URL}, clear=True):
            os.environ.pop("SECRET_KEY", None)
            with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
                import dlc_montage.core.settings.prod as prod_settings

                importlib.reload(prod_settings)

        # Placeholder or short SECRET_KEY
        for bad_secret in ("", "replace-with-your-django-secret-key", "short"):
            with patch.dict(os.environ, {"DATABASE_URL": self.VALID_URL, "SECRET_KEY": bad_secret}, clear=True):
                with pytest.raises(ImproperlyConfigured, match="SECRET_KEY"):
                    import dlc_montage.core.settings.prod as prod_settings

                    importlib.reload(prod_settings)

    def test_production_rejects_debug_true(self):
        for bad_debug in ("True", "true", "1", "yes"):
            with patch.dict(
                os.environ,
                {"DATABASE_URL": self.VALID_URL, "SECRET_KEY": self.VALID_SECRET, "DEBUG": bad_debug},
                clear=True,
            ):
                with pytest.raises(ImproperlyConfigured, match="DEBUG"):
                    import dlc_montage.core.settings.prod as prod_settings

                    importlib.reload(prod_settings)

    def test_production_accepts_postgres_and_valid_secret(self):
        with patch.dict(
            os.environ, {"DATABASE_URL": self.VALID_URL, "SECRET_KEY": self.VALID_SECRET, "DEBUG": "False"}, clear=True
        ):
            import dlc_montage.core.settings.prod as prod_settings

            importlib.reload(prod_settings)
            assert prod_settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
            assert prod_settings.DEBUG is False

    def test_production_cookie_domain_and_csrf_do_not_hardcode_example_com(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": self.VALID_URL,
                "SECRET_KEY": self.VALID_SECRET,
                "CSRF_TRUSTED_ORIGINS": "https://crm.dlc-montage.de",
                "CSRF_COOKIE_DOMAIN": ".dlc-montage.de",
                "SESSION_COOKIE_DOMAIN": ".dlc-montage.de",
            },
            clear=True,
        ):
            import dlc_montage.core.settings.prod as prod_settings

            importlib.reload(prod_settings)
            assert prod_settings.CSRF_COOKIE_DOMAIN == ".dlc-montage.de"
            assert prod_settings.SESSION_COOKIE_DOMAIN == ".dlc-montage.de"
            assert "https://crm.dlc-montage.de" in prod_settings.CSRF_TRUSTED_ORIGINS
            assert "https://example.com" not in prod_settings.CSRF_TRUSTED_ORIGINS

    def test_production_cookie_domain_defaults_to_none_when_unset(self):
        env = {"DATABASE_URL": self.VALID_URL, "SECRET_KEY": self.VALID_SECRET}
        with patch.dict(os.environ, env, clear=True):
            import dlc_montage.core.settings.prod as prod_settings

            importlib.reload(prod_settings)
            assert prod_settings.CSRF_COOKIE_DOMAIN is None
            assert prod_settings.SESSION_COOKIE_DOMAIN is None
            assert "https://example.com" not in prod_settings.CSRF_TRUSTED_ORIGINS

    def test_storages_preserves_private_storage_in_production(self):
        with patch.dict(os.environ, {"DATABASE_URL": self.VALID_URL, "SECRET_KEY": self.VALID_SECRET}, clear=True):
            import dlc_montage.core.settings.prod as prod_settings

            importlib.reload(prod_settings)
            assert "staticfiles" in prod_settings.STORAGES
            assert "private" in prod_settings.STORAGES
            assert "default" in prod_settings.STORAGES
            assert (
                prod_settings.STORAGES["staticfiles"]["BACKEND"]
                == "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
            )

    def test_base_settings_has_no_hardcoded_nextcloud_password_fallback(self):
        import dlc_montage.core.settings.base as base_settings

        with patch.dict(os.environ, {}, clear=True), patch("dotenv.load_dotenv"):
            importlib.reload(base_settings)
            assert not base_settings.NEXTCLOUD_PASSWORD

    def test_env_precedence_preserves_container_environment(self):
        import dlc_montage.core.settings.base as base_settings

        with patch.dict(os.environ, {"PROJECT_NAME": "container_injected_project_name"}, clear=True):
            importlib.reload(base_settings)
            assert base_settings.PROJECT_NAME == "container_injected_project_name"

    def test_production_enforces_strict_ssl_and_secure_cookies(self):
        with patch.dict(
            os.environ, {"DATABASE_URL": self.VALID_URL, "SECRET_KEY": self.VALID_SECRET, "DEBUG": "False"}, clear=True
        ):
            import dlc_montage.core.settings.prod as prod_settings

            importlib.reload(prod_settings)
            assert prod_settings.SECURE_SSL_REDIRECT is True
            assert prod_settings.SESSION_COOKIE_SECURE is True
            assert prod_settings.CSRF_COOKIE_SECURE is True
            assert prod_settings.LANGUAGE_COOKIE_SECURE is True
            assert prod_settings.SECURE_HSTS_SECONDS == 31536000

    def test_container_local_allows_http_loopback(self):
        with patch.dict(
            os.environ, {"DATABASE_URL": self.VALID_URL, "SECRET_KEY": self.VALID_SECRET, "DEBUG": "False"}, clear=True
        ):
            import dlc_montage.core.settings.container_local as container_local_settings

            importlib.reload(container_local_settings)
            assert container_local_settings.SECURE_SSL_REDIRECT is False
            assert container_local_settings.SESSION_COOKIE_SECURE is False
            assert container_local_settings.CSRF_COOKIE_SECURE is False
            assert container_local_settings.LANGUAGE_COOKIE_SECURE is False
            assert container_local_settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"

    def test_manifest_storage_strict_mode_is_not_globally_disabled(self):
        from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

        assert ManifestStaticFilesStorage.manifest_strict is True

    def test_session_engine_persists_to_database_or_cached_db(self):
        import dlc_montage.core.settings.modules.cache as cache_settings

        importlib.reload(cache_settings)
        assert cache_settings.SESSION_ENGINE in (
            "django.contrib.sessions.backends.cached_db",
            "django.contrib.sessions.backends.db",
        )
        assert cache_settings.SESSION_ENGINE != "django.contrib.sessions.backends.cache"


class RedisLiveSmokeTest(SimpleTestCase):
    """Direct Redis smoke test verifying independent connectivity from LocMemCache."""

    def test_direct_redis_ping_and_rw(self):
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            pytest.skip("REDIS_URL not configured for direct Redis smoke test")

        import redis

        client = redis.Redis.from_url(redis_url, socket_timeout=3.0)
        assert client.ping() is True

        test_key = "dlc:smoke:test_key"
        client.set(test_key, "smoke_value", ex=30)
        val = client.get(test_key)
        assert val == b"smoke_value"
        client.delete(test_key)


class CloudCredentialsSafetyTest(TestCase):
    """Verify external cloud credentials safety and graceful unavailable state."""

    def test_absent_nextcloud_credentials_reports_unavailable_safely(self):
        group = ProjectGroup.objects.create(name="Safety Test Group")
        site = AcObject.objects.create(group=group, name="Safety Site", project_number="9999")
        cache.clear()

        unconfigured_client = NextcloudWebDAVClient(base_url="", username="", password="")
        assert not unconfigured_client.is_configured

        summary = get_site_photo_summary(site, client=unconfigured_client)
        assert summary["status"] == "unavailable"
        assert summary["is_available"] is False
        assert summary["count"] == 0
        assert summary["photos"] == []


class HealthEndpointTest(TestCase):
    """Verify system health check endpoint contract."""

    def test_health_failure_does_not_expose_internal_exception_details(self):
        with patch("system.views.health.connection.cursor", side_effect=RuntimeError("private-db-token")), patch(
            "system.views.health.cache.set", side_effect=RuntimeError("private-cache-token")
        ):
            response = self.client.get("/health/")
        assert response.status_code == 503
        assert "private-db-token" not in response.content.decode()
        assert "private-cache-token" not in response.content.decode()

    def test_health_check_endpoint_returns_ok_status(self):
        response = self.client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert data["cache"] == "ok"

    def test_health_check_available_on_system_prefix_as_well(self):
        response = self.client.get(reverse("system:health_check"))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
