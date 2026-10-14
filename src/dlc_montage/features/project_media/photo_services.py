"""Durable, bounded photo imports; HTTP callers only enqueue database work."""

from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from time import monotonic
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from loguru import logger

from features.integrations.nextcloud.client import NextcloudWebDAVClient
from features.integrations.nextcloud.photo_sync import list_site_photos

from .models import SitePhoto, SitePhotoSyncState
from .services import validate_upload

CHECK_INTERVAL = 60
CLAIM_LEASE = 900
MAX_CLAIMS = 3


@dataclass(frozen=True)
class PhotoSyncResult:
    """Safe aggregate counters, containing no remote paths or exception messages."""

    status: str
    synced: int = 0
    unchanged: int = 0
    failed: int = 0


def _source_context(site):
    values = [site.group_id, site.group.name if site.group_id else "", site.name, site.address, site.project_number]
    return sha256(repr(values).encode()).hexdigest()


def request_site_photo_sync(site):
    """Enqueue a throttled check for an authorized site, with database work only."""
    now = timezone.now()
    context = _source_context(site)
    with transaction.atomic():
        state, _ = SitePhotoSyncState.objects.select_for_update().get_or_create(
            site=site,
            defaults={"source_context": context, "status": "pending"},
        )
        if state.status in {"queued", "processing"}:
            return state.status
        last_check = state.checked_at or state.requested_at
        if state.source_context == context and last_check and now - last_check < timedelta(seconds=CHECK_INTERVAL):
            return state.status
        state.source_context = context
        state.requested_at = now
        state.claimed_at = None
        state.status = "queued"
        state.attempts = 0
        state.next_cursor = 0
        state.failed_files = 0
        state.save()
    return "queued"


def _save_photo(site, source, content):
    """Validate before storage writes and replace the DB pointer only after success."""
    upload = ContentFile(content, name=source["name"])
    content_type = validate_upload(upload, "photo")
    source_id = sha256(source["path"].encode()).hexdigest()
    checksum = sha256(content).hexdigest()
    old = SitePhoto.objects.filter(site=site, source_id=source_id).first()
    values = {
        "source_path": source["path"],
        "source_etag": source["etag"],
        "source_modified": source["modified"],
        "checksum": checksum,
        "original_name": source["name"],
        "content_type": content_type,
        "size": len(content),
    }
    if old and old.checksum == checksum:
        SitePhoto.objects.filter(pk=old.pk).update(
            source_etag=source["etag"],
            source_modified=source["modified"],
            synced_at=timezone.now(),
        )
        return False
    photo = SitePhoto(site=site, source_id=source_id, **values)
    photo.image.save(source["name"], upload, save=False)
    try:
        with transaction.atomic():
            SitePhoto.objects.update_or_create(
                site=site,
                source_id=source_id,
                defaults={**values, "image": photo.image.name},
            )
    except Exception:
        # Only this newly written object is discarded. Existing copies are retained.
        photo.image.storage.delete(photo.image.name)
        raise
    return True


def sync_site_photos(site, *, client=None, force=False):
    """Import one batch in the isolated worker; never call this from an HTTP view."""
    state, _ = SitePhotoSyncState.objects.get_or_create(
        site=site,
        defaults={"source_context": _source_context(site), "status": "pending"},
    )
    now = timezone.now()
    if (
        not force
        and state.checked_at
        and state.source_context == _source_context(site)
        and now - state.checked_at < timedelta(seconds=CHECK_INTERVAL)
    ):
        return PhotoSyncResult("cached")
    lock_key = f"site-photo-sync:{site.pk}"
    token = uuid4().hex
    if not cache.add(lock_key, token, timeout=CLAIM_LEASE):
        return PhotoSyncResult("busy")
    synced = unchanged = failed = 0
    next_cursor = state.next_cursor
    max_files = min(100, max(1, int(getattr(settings, "PHOTO_SYNC_BATCH_SIZE", 10))))
    byte_budget = 100 * 1024 * 1024
    status = "unavailable"
    try:
        if client is None:
            client = NextcloudWebDAVClient(timeout=10)
            if not client.is_configured:
                status = "not_configured"
                return PhotoSyncResult(status)
        sources = sorted(list_site_photos(site, client), key=lambda source: source["path"])
        deadline = monotonic() + 45
        status = "ok"
        for source in sources[next_cursor : next_cursor + max_files]:
            if monotonic() >= deadline or byte_budget <= 0:
                break
            next_cursor += 1
            source_id = sha256(source["path"].encode()).hexdigest()
            old = SitePhoto.objects.filter(site=site, source_id=source_id).first()
            if old and source["etag"] and old.source_etag == source["etag"]:
                unchanged += 1
                continue
            try:
                data, _ = client.get_file(
                    source["path"],
                    max_size=min(20 * 1024 * 1024, byte_budget),
                    deadline_seconds=min(15.0, max(1.0, deadline - monotonic())),
                )
                if not data or len(data) > min(20 * 1024 * 1024, byte_budget):
                    raise ValueError("Photo exceeds import budget")
                byte_budget -= len(data)
                if _save_photo(site, source, data):
                    synced += 1
                else:
                    unchanged += 1
            except Exception as exc:
                failed += 1
                logger.bind(site_id=site.pk, error_type=type(exc).__name__).warning("Site photo import failed")
        status = "queued" if next_cursor < len(sources) else ("partial" if failed + state.failed_files else "ok")
        return PhotoSyncResult(status, synced, unchanged, failed)
    except Exception as exc:
        status = "unavailable"
        logger.bind(site_id=site.pk, error_type=type(exc).__name__).warning("Site photo listing failed")
        return PhotoSyncResult("unavailable", synced, unchanged, failed)
    finally:
        SitePhotoSyncState.objects.filter(pk=state.pk).update(
            source_context=_source_context(site),
            checked_at=timezone.now(),
            status=status,
            next_cursor=next_cursor if status == "queued" else 0,
            claimed_at=None,
            attempts=0,
            failed_files=state.failed_files + failed,
            requested_at=timezone.now() if status == "queued" else state.requested_at,
        )
        if cache.get(lock_key) == token:
            cache.delete(lock_key)
        logger.bind(site_id=site.pk, status=status, synced=synced, unchanged=unchanged, failed=failed).info(
            "Site photo sync batch finished",
        )


def process_pending_photo_syncs(*, limit=1):
    """Claim queued/expired work without holding a transaction during network I/O."""
    now = timezone.now()
    expired = now - timedelta(seconds=CLAIM_LEASE)
    SitePhotoSyncState.objects.filter(status="processing", claimed_at__lt=expired, attempts__gte=MAX_CLAIMS).update(
        status="unavailable",
        checked_at=now,
        claimed_at=None,
    )
    candidates = SitePhotoSyncState.objects.filter(
        Q(status="queued") | Q(status="processing", claimed_at__lt=expired, attempts__lt=MAX_CLAIMS),
    ).order_by("requested_at", "pk")
    processed = 0
    for state in candidates[:limit]:
        claimed = SitePhotoSyncState.objects.filter(
            pk=state.pk,
            status=state.status,
            claimed_at=state.claimed_at,
            attempts=state.attempts,
        ).update(status="processing", claimed_at=now, attempts=state.attempts + 1)
        if not claimed:
            continue
        from features.projects.models import AcObject

        site = AcObject.objects.select_related("group").get(pk=state.site_id)
        result = sync_site_photos(site, force=True)
        if result.status == "busy":
            SitePhotoSyncState.objects.filter(pk=state.pk, claimed_at=now).update(status="queued", claimed_at=None)
            continue
        processed += 1
    return processed
