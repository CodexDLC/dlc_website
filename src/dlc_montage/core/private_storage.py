"""Закрытое хранилище документов: локальная разработка или явно настроенный S3."""

from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def private_storage():
    if "private" in getattr(settings, "STORAGES", {}):
        from django.core.files.storage import storages

        return storages["private"]
    if getattr(settings, "PRIVATE_STORAGE_BACKEND", "local") == "s3":
        from storages.backends.s3 import S3Storage

        return S3Storage(
            bucket_name=settings.PRIVATE_S3_BUCKET,
            endpoint_url=settings.PRIVATE_S3_ENDPOINT,
            region_name=settings.PRIVATE_S3_REGION,
            access_key=settings.PRIVATE_S3_ACCESS_KEY,
            secret_key=settings.PRIVATE_S3_SECRET_KEY,
            default_acl=None,
            querystring_auth=True,
            file_overwrite=False,
        )
    return FileSystemStorage(
        location=getattr(settings, "PRIVATE_MEDIA_ROOT", Path(settings.BASE_DIR).parents[1] / "data" / "private")
    )
