"""Private storage: local development or explicitly configured Hetzner S3."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

PRIVATE_STORAGE_BACKEND = os.environ.get("PRIVATE_STORAGE_BACKEND", "local")
PRIVATE_MEDIA_ROOT = Path(
    os.environ.get("PRIVATE_MEDIA_ROOT", str(Path(__file__).resolve().parents[5] / "data" / "private"))
)
PRIVATE_S3_BUCKET = os.environ.get("PRIVATE_S3_BUCKET", "")
PRIVATE_S3_ENDPOINT = os.environ.get("PRIVATE_S3_ENDPOINT", "")
PRIVATE_S3_REGION = os.environ.get("PRIVATE_S3_REGION", "")
PRIVATE_S3_ACCESS_KEY = os.environ.get("PRIVATE_S3_ACCESS_KEY", "")
PRIVATE_S3_SECRET_KEY = os.environ.get("PRIVATE_S3_SECRET_KEY", "")
if PRIVATE_STORAGE_BACKEND not in ("local", "s3"):
    raise ImproperlyConfigured("PRIVATE_STORAGE_BACKEND must be local or s3.")
if PRIVATE_STORAGE_BACKEND == "s3" and not all(
    (PRIVATE_S3_BUCKET, PRIVATE_S3_ENDPOINT, PRIVATE_S3_REGION, PRIVATE_S3_ACCESS_KEY, PRIVATE_S3_SECRET_KEY)
):
    raise ImproperlyConfigured("All PRIVATE_S3_* settings are required for S3. No local fallback is used.")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if PRIVATE_STORAGE_BACKEND == "s3":
    STORAGES["private"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": PRIVATE_S3_BUCKET,
            "endpoint_url": PRIVATE_S3_ENDPOINT,
            "region_name": PRIVATE_S3_REGION,
            "access_key": PRIVATE_S3_ACCESS_KEY,
            "secret_key": PRIVATE_S3_SECRET_KEY,
            "default_acl": None,
            "querystring_auth": True,
            "file_overwrite": False,
        },
    }
else:
    STORAGES["private"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": str(PRIVATE_MEDIA_ROOT),
        },
    }
