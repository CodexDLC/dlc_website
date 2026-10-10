"""Create a private deployment env without printing or replacing existing secrets."""

import argparse
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-env", type=Path, default=Path(".env"))
    parser.add_argument("--output", type=Path, default=Path(".env.prod"))
    parser.add_argument("--fresh-database", action="store_true")
    args = parser.parse_args()
    existing = dotenv_values(args.source_env) if args.source_env.exists() else {}
    field_key = existing.get("FIELD_ENCRYPTION_KEY")
    if not field_key:
        if not args.fresh_database:
            parser.error("Existing FIELD_ENCRYPTION_KEY required; use --fresh-database only for a new database.")
        field_key = Fernet.generate_key().decode("ascii")
    Fernet(field_key.encode("ascii"))
    values = {
        "COMPOSE_PROJECT_NAME": "dlc",
        "DEBUG": "False",
        "SECRET_KEY": secrets.token_hex(48),
        "FIELD_ENCRYPTION_KEY": field_key,
        "DLC_DB_NAME": "dlc_montage",
        "DLC_DB_USER": "dlc_montage",
        "DLC_DB_PASSWORD": secrets.token_hex(32),
        "DLC_PROD_WEB_PORT": "8000",
        "ALLOWED_HOSTS": "dlc.pinlite.dev,localhost,127.0.0.1",
        "CSRF_TRUSTED_ORIGINS": "https://dlc.pinlite.dev",
        "TEST_SITE_BASE_URL": "https://dlc.pinlite.dev/",
        "TEST_CANONICAL_DOMAIN": "https://dlc.pinlite.dev",
        "PRIVATE_STORAGE_BACKEND": "local",
    }
    try:
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.error("Output already exists; refusing to rotate secrets or overwrite it.")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("# Private deployment configuration. Never commit or share in chat.\n")
        for key, value in values.items():
            stream.write(f"{key}={value}\n")
    print(f"Created {args.output}; secret values were not printed.")


if __name__ == "__main__":
    main()
