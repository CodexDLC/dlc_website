"""Закрытые вложения общих проектов и AC-объектов."""

from pathlib import Path
from typing import ClassVar
from uuid import uuid4

from core.private_storage import photos_storage, private_storage
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def attachment_path(instance, filename):
    branch = f"ac/{instance.site_id}" if instance.site_id else "general"
    return f"projects/{instance.group_id}/{branch}/{instance.kind}/{uuid4().hex}{Path(filename).suffix.lower()}"


class ProjectFile(models.Model):
    group = models.ForeignKey("projects.ProjectGroup", on_delete=models.PROTECT, related_name="files")
    site = models.ForeignKey("projects.AcObject", on_delete=models.PROTECT, null=True, blank=True, related_name="files")
    kind = models.CharField(
        max_length=16, choices=[("photo", _("Итоговое фото")), ("plan", _("План")), ("document", _("Документ"))]
    )
    file = models.FileField(storage=private_storage, upload_to=attachment_path, max_length=500)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    caption = models.CharField(max_length=500, blank=True)
    is_public = models.BooleanField(default=False)
    customer_visible = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar = ["-created_at", "-pk"]

    @property
    def is_image(self):
        return self.content_type.startswith("image/")

    @property
    def is_pdf(self):
        return self.content_type == "application/pdf"

    @property
    def can_preview(self):
        return self.is_image or self.is_pdf


def site_photo_path(instance, filename):
    """Keep imported photos under an opaque, site-specific private storage key."""
    return f"site-photos/{instance.site_id}/{uuid4().hex}{Path(filename).suffix.lower()}"


class SitePhoto(models.Model):
    """A verified local/S3 copy that remains usable independently of Nextcloud."""

    site = models.ForeignKey("projects.AcObject", on_delete=models.PROTECT, related_name="stored_photos")
    source_id = models.CharField(max_length=64)
    source_path = models.CharField(max_length=1500)
    source_etag = models.CharField(max_length=255, blank=True)
    source_modified = models.CharField(max_length=255, blank=True)
    checksum = models.CharField(max_length=64)
    image = models.FileField(storage=photos_storage, upload_to=site_photo_path, max_length=500)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=64)
    size = models.PositiveIntegerField()
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar = ["original_name", "pk"]
        constraints: ClassVar = [
            models.UniqueConstraint(fields=["site", "source_id"], name="unique_site_photo_source"),
        ]


class SitePhotoSyncState(models.Model):
    """Persist the last bounded check, including failures, to throttle page refreshes."""

    site = models.OneToOneField("projects.AcObject", on_delete=models.CASCADE, related_name="photo_sync_state")
    source_context = models.CharField(max_length=64)
    checked_at = models.DateTimeField(null=True, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_cursor = models.PositiveIntegerField(default=0)
    failed_files = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=24)
