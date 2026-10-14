"""Persistent photos, safe imports and the database-only enqueue boundary."""

from datetime import timedelta
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.storage import InMemoryStorage
from django.utils import timezone
from features.integrations.nextcloud.client import NextcloudWebDAVClient, NextcloudWebDAVError
from features.project_media.models import SitePhoto, SitePhotoSyncState
from features.project_media.photo_selectors import get_site_photo, get_site_photo_summary
from features.project_media.photo_services import (
    CLAIM_LEASE,
    process_pending_photo_syncs,
    request_site_photo_sync,
    sync_site_photos,
)
from features.projects.models import AcObject, ProjectGroup
from PIL import Image

pytestmark = pytest.mark.django_db


def image_bytes(color="red"):
    output = BytesIO()
    Image.new("RGB", (8, 8), color).save(output, format="PNG")
    return output.getvalue()


class PhotoSource:
    """A read-only source double that serves one exact site folder."""

    def __init__(self, site):
        self.folder = f"DLC Montage/AC/{site.group.name}/{site.project_number} - {site.name}/Fotos"
        self.items = [{"name": "roof.png", "is_directory": False, "etag": "v1"}]
        self.data = image_bytes()
        self.get_calls = []
        self.list_calls = []
        self.fail = False

    def list_folder(self, folder):
        self.list_calls.append(folder)
        if self.fail:
            raise OSError("source unavailable")
        return self.items if folder == self.folder else []

    def get_file(self, path, *, max_size, deadline_seconds):
        assert path.startswith(self.folder + "/")
        assert max_size <= 20 * 1024 * 1024
        assert deadline_seconds <= 15.0
        self.get_calls.append(path)
        return self.data, "text/html"


@pytest.fixture
def photo_setup(monkeypatch):
    cache.clear()
    user = get_user_model().objects.create_user(username="photo-owner")
    group = ProjectGroup.objects.create(name="Anlage Photos", responsible=user, has_ac=True)
    site = AcObject.objects.create(group=group, name="Haus 1", project_number="2026-901")
    storage = InMemoryStorage()
    monkeypatch.setattr(SitePhoto._meta.get_field("image"), "storage", storage)
    return site, PhotoSource(site), storage


def test_verified_copy_is_persisted_and_repeat_is_idempotent(photo_setup):
    site, source, storage = photo_setup
    result = sync_site_photos(site, client=source)
    assert result.status == "ok"
    assert result.synced == 1
    photo = SitePhoto.objects.get(site=site)
    assert photo.content_type == "image/png"
    assert storage.open(photo.image.name).read() == source.data
    assert sync_site_photos(site, client=source).status == "cached"
    assert sync_site_photos(site, client=source, force=True).unchanged == 1
    assert len(source.get_calls) == 1
    assert SitePhoto.objects.filter(site=site).count() == 1


def test_changed_source_replaces_pointer_and_keeps_old_copy(photo_setup):
    site, source, storage = photo_setup
    sync_site_photos(site, client=source)
    photo = SitePhoto.objects.get(site=site)
    old_name = photo.image.name
    source.items[0]["etag"] = "v2"
    source.data = image_bytes("blue")
    assert sync_site_photos(site, client=source, force=True).synced == 1
    photo.refresh_from_db()
    assert photo.image.name != old_name
    assert photo.source_etag == "v2"
    assert storage.exists(old_name)
    assert storage.open(photo.image.name).read() == source.data
    assert SitePhoto.objects.filter(site=site).count() == 1


def test_source_outage_keeps_saved_photo_available_without_storage_io(photo_setup, monkeypatch):
    site, source, storage = photo_setup
    sync_site_photos(site, client=source)
    source.fail = True
    assert sync_site_photos(site, client=source, force=True).status == "unavailable"

    def forbidden(*args, **kwargs):
        raise AssertionError("Summary must not contact storage")

    monkeypatch.setattr(storage, "url", forbidden)
    monkeypatch.setattr(storage, "exists", forbidden)
    summary = get_site_photo_summary(site)
    assert summary["count"] == 1
    assert summary["is_available"] is True
    assert summary["sync_status"] == "unavailable"
    assert summary["photos"][0]["name"] == "roof.png"


def test_invalid_replacement_preserves_existing_pointer(photo_setup):
    site, source, storage = photo_setup
    sync_site_photos(site, client=source)
    photo = SitePhoto.objects.get(site=site)
    old_name = photo.image.name
    source.items[0]["etag"] = "v2"
    source.data = b"\x89PNG\r\n\x1a\nnot-an-image"
    result = sync_site_photos(site, client=source, force=True)
    assert result.status == "partial"
    assert result.failed == 1
    photo.refresh_from_db()
    assert photo.image.name == old_name
    assert photo.source_etag == "v1"
    assert storage.exists(old_name)


def test_missing_remote_file_does_not_delete_saved_copy(photo_setup):
    site, source, _ = photo_setup
    sync_site_photos(site, client=source)
    source.items = []
    assert sync_site_photos(site, client=source, force=True).status == "ok"
    assert SitePhoto.objects.filter(site=site).count() == 1


def test_source_without_etag_uses_digest_to_avoid_duplicate_storage(photo_setup):
    site, source, _ = photo_setup
    source.items[0].pop("etag")
    sync_site_photos(site, client=source)
    photo = SitePhoto.objects.get(site=site)
    old_name = photo.image.name
    assert sync_site_photos(site, client=source, force=True).unchanged == 1
    photo.refresh_from_db()
    assert photo.image.name == old_name


def test_hostile_paths_are_never_downloaded(photo_setup):
    site, source, _ = photo_setup
    source.items = [
        {"name": "../foreign.png"},
        {"name": "foreign.png", "relative_path": "DLC Montage/AC/Other/Fotos/foreign.png"},
        {"name": "nested.png", "relative_path": f"{source.folder}/nested/nested.png"},
        {"name": "image.svg"},
    ]
    assert sync_site_photos(site, client=source).synced == 0
    assert source.get_calls == []
    assert SitePhoto.objects.count() == 0


def test_photo_lookup_is_bound_to_site(photo_setup):
    site, source, _ = photo_setup
    sync_site_photos(site, client=source)
    photo = SitePhoto.objects.get(site=site)
    other = AcObject.objects.create(group=site.group, name="Haus 2")
    assert get_site_photo(site, photo.pk) == photo
    assert get_site_photo(other, photo.pk) is None


def test_enqueue_is_db_only_and_rate_limited(photo_setup, monkeypatch):
    site, _, _ = photo_setup

    def forbidden(*args, **kwargs):
        raise AssertionError("Web enqueue must not perform photo I/O")

    monkeypatch.setattr("features.project_media.photo_services.NextcloudWebDAVClient", forbidden)
    assert request_site_photo_sync(site) == "queued"
    assert request_site_photo_sync(site) == "queued"
    state = SitePhotoSyncState.objects.get(site=site)
    state.status = "ok"
    state.checked_at = timezone.now()
    state.save()
    assert request_site_photo_sync(site) == "ok"
    site.name = "Haus Renamed"
    assert request_site_photo_sync(site) == "queued"


def test_worker_batches_make_durable_progress(photo_setup, settings, monkeypatch):
    site, source, _ = photo_setup
    settings.PHOTO_SYNC_BATCH_SIZE = 1
    source.items += [{"name": "second.png", "etag": "v1"}]
    monkeypatch.setattr("features.project_media.photo_services.NextcloudWebDAVClient", lambda **kwargs: source)
    source.is_configured = True
    request_site_photo_sync(site)
    assert process_pending_photo_syncs() == 1
    state = SitePhotoSyncState.objects.get(site=site)
    assert state.status == "queued"
    assert state.next_cursor == 1
    assert SitePhoto.objects.count() == 1
    assert process_pending_photo_syncs() == 1
    state.refresh_from_db()
    assert state.status == "ok"
    assert state.next_cursor == 0
    assert SitePhoto.objects.count() == 2
    assert process_pending_photo_syncs() == 0


def test_expired_worker_claim_recovers_and_exhausted_claim_stops(photo_setup, monkeypatch):
    site, source, _ = photo_setup
    source.is_configured = True
    monkeypatch.setattr("features.project_media.photo_services.NextcloudWebDAVClient", lambda **kwargs: source)
    request_site_photo_sync(site)
    state = SitePhotoSyncState.objects.get(site=site)
    state.status = "processing"
    state.claimed_at = timezone.now() - timedelta(seconds=CLAIM_LEASE + 1)
    state.attempts = 1
    state.save()
    assert process_pending_photo_syncs() == 1
    state.refresh_from_db()
    assert state.status == "ok"
    state.status = "processing"
    state.claimed_at = timezone.now() - timedelta(seconds=CLAIM_LEASE + 1)
    state.attempts = 3
    state.save()
    assert process_pending_photo_syncs() == 0
    state.refresh_from_db()
    assert state.status == "unavailable"


def test_cache_lock_blocks_concurrent_sync(photo_setup):
    site, source, _ = photo_setup
    cache.set(f"site-photo-sync:{site.pk}", "other-worker", timeout=CLAIM_LEASE)
    assert sync_site_photos(site, client=source).status == "busy"
    assert source.list_calls == []


def test_database_failure_preserves_existing_copy(photo_setup, monkeypatch):
    site, source, storage = photo_setup
    sync_site_photos(site, client=source)
    photo = SitePhoto.objects.get(site=site)
    old_name = photo.image.name
    source.items[0]["etag"] = "v2"
    source.data = image_bytes("blue")

    def fail_save(*args, **kwargs):
        raise OSError("database failure")

    monkeypatch.setattr(SitePhoto.objects, "update_or_create", fail_save)
    assert sync_site_photos(site, client=source, force=True).failed == 1
    photo.refresh_from_db()
    assert photo.image.name == old_name
    assert storage.exists(old_name)


@pytest.mark.django_db(transaction=True)
def test_worker_network_io_runs_without_database_transaction(photo_setup, monkeypatch):
    from django.db import connection

    site, source, _ = photo_setup
    original_list = source.list_folder

    def list_without_transaction(folder):
        assert not connection.in_atomic_block
        return original_list(folder)

    source.list_folder = list_without_transaction
    source.is_configured = True
    monkeypatch.setattr("features.project_media.photo_services.NextcloudWebDAVClient", lambda **kwargs: source)
    request_site_photo_sync(site)
    assert process_pending_photo_syncs() == 1
    assert SitePhoto.objects.filter(site=site).count() == 1


def test_nextcloud_listing_exposes_revision_metadata():
    response = Mock(status_code=207, is_redirect=False)
    response.text = """<d:multistatus xmlns:d="DAV:">
      <d:response><d:href>/remote.php/dav/files/DLC/Fotos/photo.png</d:href>
      <d:propstat><d:prop><d:resourcetype/><d:getetag>revision-2</d:getetag>
      <d:getlastmodified>Wed, 14 Oct 2026 12:00:00 GMT</d:getlastmodified></d:prop>
      <d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>
    </d:multistatus>"""
    source = NextcloudWebDAVClient(base_url="https://cloud.test/remote.php/dav/files/DLC/", username="DLC")
    with patch("features.integrations.nextcloud.client.requests.request", return_value=response):
        item = source.list_folder("Fotos")[0]
    assert item["etag"] == "revision-2"
    assert item["modified"] == "Wed, 14 Oct 2026 12:00:00 GMT"


def test_nextcloud_streaming_download_stops_at_wall_time_budget():
    response = Mock(status_code=200, is_redirect=False)
    response.headers = {}
    response.iter_content.return_value = [b"image-chunk"]
    source = NextcloudWebDAVClient(base_url="https://cloud.test/remote.php/dav/files/DLC/", username="DLC")
    with (
        patch("features.integrations.nextcloud.client.requests.get", return_value=response),
        patch("features.integrations.nextcloud.client.monotonic", side_effect=[100.0, 106.0]),
        pytest.raises(NextcloudWebDAVError, match="time budget"),
    ):
        source.get_file("Fotos/photo.png", deadline_seconds=5)
    response.close.assert_called_once()


def test_queued_continuations_do_not_starve_another_site(photo_setup, settings, monkeypatch):
    site, source, _ = photo_setup
    other = AcObject.objects.create(group=site.group, name="Haus 2", project_number="2026-902")
    other_source = PhotoSource(other)
    settings.PHOTO_SYNC_BATCH_SIZE = 1
    source.items += [{"name": "second.png", "etag": "v1"}]
    source.is_configured = other_source.is_configured = True
    sources = iter([source, other_source])
    monkeypatch.setattr("features.project_media.photo_services.NextcloudWebDAVClient", lambda **kwargs: next(sources))
    request_site_photo_sync(site)
    request_site_photo_sync(other)
    assert process_pending_photo_syncs() == 1
    assert SitePhotoSyncState.objects.get(site=site).status == "queued"
    assert process_pending_photo_syncs() == 1
    assert SitePhoto.objects.filter(site=other).count() == 1
    assert SitePhotoSyncState.objects.get(site=site).status == "queued"
