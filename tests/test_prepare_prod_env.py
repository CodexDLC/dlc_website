"""Deployment secrets retain encryption identity and cannot be silently replaced."""

import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_prod_env.py"


def invoke_generator(source, output, *extra):
    return subprocess.run(  # noqa: S603 - fixed project script; test-owned temporary paths only.
        [sys.executable, str(SCRIPT), "--source-env", str(source), "--output", str(output), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def test_preserves_existing_field_key_without_disclosing_secrets(tmp_path):
    source = tmp_path / "source.env"
    output = tmp_path / "deployment.env"
    field_key = Fernet.generate_key().decode("ascii")
    source.write_text(f"FIELD_ENCRYPTION_KEY={field_key}\n", encoding="utf-8")

    result = invoke_generator(source, output)

    assert result.returncode == 0, result.stderr
    generated = dotenv_values(output)
    assert generated["FIELD_ENCRYPTION_KEY"] == field_key
    assert generated["SECRET_KEY"] and generated["DLC_DB_PASSWORD"]
    for name in ("FIELD_ENCRYPTION_KEY", "SECRET_KEY", "DLC_DB_PASSWORD"):
        assert generated[name] not in result.stdout + result.stderr


def test_refuses_overwriting_existing_deployment_secrets(tmp_path):
    source = tmp_path / "missing.env"
    output = tmp_path / "deployment.env"
    original = b"preserved deployment configuration\n"
    output.write_bytes(original)

    result = invoke_generator(source, output, "--fresh-database")

    assert result.returncode != 0
    assert "refusing to rotate secrets or overwrite" in result.stderr
    assert output.read_bytes() == original


def test_missing_field_key_requires_explicit_new_database(tmp_path):
    source = tmp_path / "missing.env"
    output = tmp_path / "deployment.env"

    rejected = invoke_generator(source, output)

    assert rejected.returncode != 0
    assert "Existing FIELD_ENCRYPTION_KEY required" in rejected.stderr
    assert not output.exists()

    accepted = invoke_generator(source, output, "--fresh-database")

    assert accepted.returncode == 0, accepted.stderr
    values = dotenv_values(output)
    Fernet(values["FIELD_ENCRYPTION_KEY"].encode("ascii"))
