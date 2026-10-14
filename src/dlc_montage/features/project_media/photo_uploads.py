"""Website photo uploads and isolated, durable full-image Nextcloud mirroring."""

import re
from datetime import timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from loguru import logger
from PIL import Image, ImageOps

from features.integrations.nextcloud.client import (
    NextcloudUploadConflict,
    NextcloudUploadPermanentError,
    NextcloudWebDAVClient,
    NextcloudWebDAVError,
)
from features.integrations.nextcloud.services import get_site_folder_path

from .models import SitePhoto
from .photo_policies import can_upload_site_photos
from .services import validate_upload


def build_thumbnail(content):
    """Create an oriented, aspect-preserving preview while retaining full original bytes."""
    with Image.open(BytesIO(content)) as original:
        picture = ImageOps.exif_transpose(original)
        picture.thumbnail((480, 480), Image.Resampling.LANCZOS)
        if picture.mode not in {"RGB", "RGBA"}:
            picture = picture.convert("RGBA" if "transparency" in picture.info else "RGB")
        output = BytesIO()
        picture.save(output, format="WEBP", quality=82, method=4)
        return output.getvalue()


def _cleanup_new_files(photo):
    for field in (photo.image, photo.thumbnail):
        if field and field._committed:
            try:
                field.storage.delete(field.name)
            except Exception as exc:
                logger.bind(error_type=type(exc).__name__).warning("New photo object cleanup failed")


def save_new_photo_file(photo, field_name, filename, content):
    """Remember our opaque key before I/O so a lost save response can be cleaned."""
    field = getattr(photo, field_name)
    field.name = field.field.generate_filename(photo, filename)
    field._committed = True
    field.name = field.storage.save(field.name, content, max_length=field.field.max_length)


def upload_site_photo(*, actor, site, upload):
    """Save validated full+thumbnail, then queue a mirror without calling Nextcloud."""
    if not can_upload_site_photos(actor, site):
        raise PermissionDenied
    name = Path(upload.name.replace("\\", "/")).name
    if not name or len(name) > 255 or any(ord(character) < 32 for character in name):
        raise ValidationError("Invalid photo filename")
    content_type = validate_upload(upload, "photo")
    content = upload.read(20 * 1024 * 1024 + 1)
    if not content or len(content) > 20 * 1024 * 1024:
        raise ValidationError("Photo exceeds the upload size limit")
    preview = build_thumbnail(content)
    identity = uuid4().hex
    safe_name = re.sub(r"[^\w.\-]", "_", name)
    remote_name = f"{identity}-{safe_name[:220]}"
    if Path(remote_name).suffix.lower() != Path(name).suffix.lower():
        remote_name = f"{identity}-{safe_name[:210]}{Path(name).suffix.lower()}"
    photo = SitePhoto(
        site=site,
        source_id=sha256(f"upload:{identity}".encode()).hexdigest(),
        source_kind="uploaded",
        uploaded_by=actor,
        remote_name=remote_name,
        original_name=name,
        content_type=content_type,
        size=len(content),
        checksum=sha256(content).hexdigest(),
        thumbnail_content_type="image/webp",
        mirror_status="queued",
        mirror_next_attempt_at=timezone.now(),
    )
    try:
        save_new_photo_file(photo, "image", name, ContentFile(content))
        save_new_photo_file(photo, "thumbnail", "preview.webp", ContentFile(preview))
        with transaction.atomic():
            photo.save()
    except Exception:
        _cleanup_new_files(photo)
        raise
    return photo


class _DiscoveryReader:
    """Detect suppressed discovery errors before allowing folder creation."""

    def __init__(self, client):
        self.client = client
        self.error = None

    def list_folder(self, *args, **kwargs):
        try:
            return self.client.list_folder(*args, **kwargs)
        except Exception as exc:
            self.error = exc
            raise


def mirror_site_photo(photo, *, client=None):
    """Mirror only the unchanged full image; repeat PUT safely after lost responses."""
    client = client or NextcloudWebDAVClient(timeout=10)
    if not client.is_configured:
        raise NextcloudUploadPermanentError("Nextcloud is not configured")
    reader = _DiscoveryReader(client)
    folder = f"{get_site_folder_path(photo.site, client=reader).strip('/')}/Fotos"
    if reader.error:
        raise reader.error
    if any(part in {".", ".."} for part in folder.split("/")) or "\\" in folder:
        raise NextcloudUploadPermanentError("Invalid site folder")
    if not client.ensure_folder(folder):
        raise NextcloudUploadPermanentError("Photo folder could not be prepared")
    destination = f"{folder}/{photo.remote_name}"
    if not photo.remote_name or "/" in photo.remote_name or "\\" in photo.remote_name or len(destination) > 1500:
        raise NextcloudUploadPermanentError("Invalid photo destination")
    # Bind before PUT: any inbound listing of the resulting object resolves this record.
    source_id = sha256(destination.encode()).hexdigest()
    SitePhoto.objects.filter(pk=photo.pk).update(source_id=source_id, source_path=destination)
    with photo.image.open("rb") as original:
        content = original.read(20 * 1024 * 1024 + 1)
    if len(content) != photo.size or sha256(content).hexdigest() != photo.checksum:
        raise NextcloudUploadPermanentError("Stored original does not match its checksum")
    try:
        etag = client.put_file(destination, content, content_type=photo.content_type)
    except NextcloudUploadConflict:
        existing, _ = client.get_file(destination, max_size=20 * 1024 * 1024, deadline_seconds=15)
        if sha256(existing).hexdigest() != photo.checksum:
            raise NextcloudUploadPermanentError("Existing remote object belongs to another upload") from None
        etag = ""
    SitePhoto.objects.filter(pk=photo.pk).update(
        mirror_status="ok",
        mirror_claimed_at=None,
        mirror_next_attempt_at=None,
        source_etag=etag,
    )
    return "ok"


def process_pending_photo_mirrors(*, limit=1):
    """Claim outbound work and retry temporary errors at most three times."""
    now = timezone.now()
    expired = now - timedelta(seconds=900)
    SitePhoto.objects.filter(mirror_status="processing", mirror_claimed_at__lt=expired, mirror_attempts__gte=3).update(
        mirror_status="failed",
        mirror_claimed_at=None,
        mirror_next_attempt_at=None,
    )
    candidates = (
        SitePhoto.objects.filter(source_kind="uploaded")
        .filter(
            Q(mirror_status="queued", mirror_next_attempt_at__lte=now)
            | Q(mirror_status="processing", mirror_claimed_at__lt=expired, mirror_attempts__lt=3),
        )
        .order_by("mirror_next_attempt_at", "pk")
    )
    count = 0
    for photo in candidates.select_related("site__group")[:limit]:
        claim = SitePhoto.objects.filter(
            pk=photo.pk,
            mirror_status=photo.mirror_status,
            mirror_claimed_at=photo.mirror_claimed_at,
            mirror_attempts=photo.mirror_attempts,
        ).update(mirror_status="processing", mirror_claimed_at=now, mirror_attempts=photo.mirror_attempts + 1)
        if not claim:
            continue
        try:
            mirror_site_photo(photo)
        except Exception as exc:
            attempts = photo.mirror_attempts + 1
            retry = isinstance(exc, NextcloudWebDAVError) and not isinstance(exc, NextcloudUploadPermanentError)
            retry = retry and attempts < 3
            SitePhoto.objects.filter(pk=photo.pk).update(
                mirror_status="queued" if retry else "failed",
                mirror_claimed_at=None,
                mirror_next_attempt_at=now + timedelta(seconds=60 * attempts) if retry else None,
            )
            logger.bind(photo_id=photo.pk, error_type=type(exc).__name__, attempt=attempts).warning(
                "Photo mirror failed"
            )
        count += 1
    return count
