"""Read saved photos without contacting either Nextcloud or object storage."""

from pathlib import Path

from .models import SitePhoto, SitePhotoSyncState


def get_site_photo_summary(site, *, include_photos=True):
    """Return counts and optional identifiers for an already authorized site."""
    photos = SitePhoto.objects.filter(site=site)
    state = SitePhotoSyncState.objects.filter(site=site).first()
    count = photos.count()
    successful = state is not None and state.status in {"ok", "partial"}
    status = "ok" if count or successful else (state.status if state else "pending")
    return {
        "status": status,
        "sync_status": state.status if state else "pending",
        "is_available": bool(count or successful),
        "has_photos": count > 0,
        "count": count,
        "photos": [
            {
                "id": photo.pk,
                "name": photo.original_name,
                "is_previewable": True,
                "extension": Path(photo.original_name).suffix.lower(),
                "version": photo.checksum[:16],
            }
            for photo in photos.only("pk", "original_name", "checksum")
        ]
        if include_photos
        else [],
        "error": None,
    }


def get_site_photo(site, photo_id):
    """Resolve a persisted identifier only within the caller's authorized site."""
    return SitePhoto.objects.filter(site=site, pk=photo_id).first()
