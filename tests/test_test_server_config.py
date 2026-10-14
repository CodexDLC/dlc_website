"""Black-box checks for the future test-server Compose configuration."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "compose.test-server.yml"
DOCKER_ENV_KEYS = (
    "PATH",
    "SystemRoot",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "PROGRAMFILES",
    "PROGRAMDATA",
)


@pytest.mark.parametrize("key_line", ["", "FIELD_ENCRYPTION_KEY="])
def test_django_compose_rejects_missing_or_empty_encryption_key(tmp_path, key_line):
    """Runtime containers cannot silently encrypt data with a shared default key."""
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker Compose CLI is unavailable")
    env_file = tmp_path / "missing-encryption-key.env"
    env_file.write_text(f"DLC_DB_PASSWORD=synthetic_database_password\n{key_line}\n", encoding="utf-8")
    env = {key: os.environ[key] for key in DOCKER_ENV_KEYS if key in os.environ}
    result = subprocess.run(  # noqa: S603 - fixed Compose command with synthetic configuration
        [
            docker,
            "compose",
            "--env-file",
            str(env_file),
            "-f",
            str(ROOT / "deploy" / "compose.infra.yml"),
            "-f",
            str(ROOT / "deploy" / "compose.django.yml"),
            "config",
            "--quiet",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "FIELD_ENCRYPTION_KEY" in result.stderr


def test_test_server_compose_requires_site_and_storage_configuration(tmp_path):
    """Compose must reject an unconfigured test-server environment."""
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker Compose CLI is unavailable")

    env_file = tmp_path / "missing-test-site.env"
    env_file.write_text(
        "\n".join(
            (
                "DLC_DB_PASSWORD=synthetic_database_password",
                "SECRET_KEY=synthetic-test-secret-key-at-least-32-chars",
                "FIELD_ENCRYPTION_KEY=synthetic-encryption-key",
                "ALLOWED_HOSTS=test.invalid",
                "CSRF_TRUSTED_ORIGINS=https://test.invalid",
                "DLC_IMAGE_TAG=synthetic-release",
            )
        ),
        encoding="utf-8",
    )
    env = {key: os.environ[key] for key in DOCKER_ENV_KEYS if key in os.environ}
    result = subprocess.run(  # noqa: S603 - fixed Compose command, synthetic environment
        [docker, "compose", "--env-file", str(env_file), "-f", str(COMPOSE), "config", "--quiet"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "TEST_SITE_BASE_URL" in result.stderr


def test_test_server_compose_keeps_internal_services_private_and_noindex(tmp_path):
    """The resolved config must keep PostgreSQL/Redis private and test indexing disabled."""
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker Compose CLI is unavailable")

    env_file = tmp_path / "test-server.env"
    env_file.write_text(
        "\n".join(
            (
                "DLC_DB_PASSWORD=synthetic_database_password",
                "SECRET_KEY=synthetic-test-secret-key-at-least-32-chars",
                "FIELD_ENCRYPTION_KEY=synthetic-encryption-key",
                "ALLOWED_HOSTS=test.invalid",
                "CSRF_TRUSTED_ORIGINS=https://test.invalid",
                "TEST_SITE_BASE_URL=https://test.invalid/",
                "TEST_CANONICAL_DOMAIN=https://test.invalid",
                "PRIVATE_STORAGE_BACKEND=local",
                "DLC_IMAGE_TAG=v0.0.0-test",
            )
        ),
        encoding="utf-8",
    )
    env = {key: os.environ[key] for key in DOCKER_ENV_KEYS if key in os.environ}
    result = subprocess.run(  # noqa: S603 - fixed Compose command, synthetic environment
        [docker, "compose", "--env-file", str(env_file), "-f", str(COMPOSE), "config", "--format", "json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    services = json.loads(result.stdout)["services"]
    assert services["web"]["environment"]["TEST_SITE_NOINDEX"] == "True"
    assert services["web"]["environment"]["SITE_BASE_URL"] == "https://test.invalid/"
    assert services["web"]["environment"]["PRIVATE_STORAGE_BACKEND"] == "local"
    assert services["web"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert not services["db"].get("ports")
    assert not services["redis"].get("ports")
    assert "X-Forwarded-Proto" in services["web"]["healthcheck"]["test"][-1]
