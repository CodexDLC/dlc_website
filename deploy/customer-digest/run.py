"""Read only dedicated digest variables freshly for each existing-web command."""

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

ENV_PATH = Path("/srv/dlc/shared/.env.prod")
CONTAINER = "dlc-web-1"
ALLOWED = {
    "CUSTOMER_DIGEST_MODE", "CUSTOMER_DIGEST_ACTOR_ID", "CUSTOMER_DIGEST_RECIPIENT_USER_ID",
    "CUSTOMER_DIGEST_CLIENT_ID", "CUSTOMER_DIGEST_RECIPIENT_EMAIL", "CUSTOMER_DIGEST_FROM_EMAIL",
    "CUSTOMER_DIGEST_BASE_URL", "CUSTOMER_DIGEST_SMTP_HOST", "CUSTOMER_DIGEST_SMTP_PORT",
    "CUSTOMER_DIGEST_SMTP_USER", "CUSTOMER_DIGEST_SMTP_PASSWORD", "CUSTOMER_DIGEST_SMTP_TIMEOUT",
}
DEFAULTS = {
    "CUSTOMER_DIGEST_MODE": "test", "CUSTOMER_DIGEST_SMTP_HOST": "smtp.gmail.com",
    "CUSTOMER_DIGEST_SMTP_PORT": "587", "CUSTOMER_DIGEST_SMTP_TIMEOUT": "30",
    "CUSTOMER_DIGEST_FROM_EMAIL": "primecodex@gmail.com", "CUSTOMER_DIGEST_SMTP_USER": "primecodex@gmail.com",
}


def read_mail_environment(path):
    """Accept literal KEY=value lines, with optional matching quotes; never evaluate shell."""
    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or key not in ALLOWED:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if any(char in value for char in "\r\n\0") or not re.fullmatch(r"[A-Z_]+", key):
            raise ValueError("invalid_mail_environment")
        values[key] = value
    # Explicitly clear absent settings so a removed password cannot survive in container env.
    return "".join(f"{key}={values.get(key, DEFAULTS.get(key, ''))}\n" for key in sorted(ALLOWED))


def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--scheduled", action="store_true")
    action.add_argument("--send", action="store_true")
    action.add_argument("--check-smtp", action="store_true")
    parser.add_argument("--work-date")
    args = parser.parse_args()
    try:
        content = read_mail_environment(ENV_PATH)
    except (OSError, ValueError):
        print("customer_digest_environment_unavailable")
        return 1
    fd, name = tempfile.mkstemp(prefix="dlc-digest-", suffix=".env")
    try:
        os.chmod(name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        command = [
            "docker", "exec", "--env-file", name, CONTAINER,
            "python", "src/dlc_montage/manage.py", "customer_digest",
        ]
        if args.scheduled:
            command.append("--scheduled")
        elif args.send:
            command.append("--send")
        elif args.check_smtp:
            command.append("--check-smtp")
        if args.work_date:
            command.extend(["--work-date", args.work_date])
        return subprocess.run(command, check=False).returncode  # noqa: S603
    finally:
        Path(name).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
