"""Website-first originals/previews and durable, idempotent outbound mirroring."""

from hashlib import sha256
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from features.integrations.nextcloud.client import (
    NextcloudUploadConflict,
    NextcloudUploadPermanentError,
    NextcloudWebDAVClient,
    NextcloudWebDAVError,
)
from features.project_media.models import SitePhoto
from features.project_media.photo_policies import can_upload_site_photos
from features.project_media.photo_selectors import get_site_photo_summary
from features.project_media.photo_services import sync_site_photos, upload_site_photo
from features.project_media.photo_uploads import mirror_site_photo, process_pending_photo_mirrors
from features.projects.models import AcObject, ProjectGroup
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_upload(monkeypatch):
    cache.clear()
    actor = get_user_model().objects.create_user(username="photo-uploader", is_superuser=True)
    group = ProjectGroup.objects.create(name="Photo Group", responsible=actor, has_ac=True)
    site = AcObject.objects.create(group=group, name="Haus 1", project_number="2026-921")
    storage = InMemoryStorage()
    for field in ("image", "thumbnail"):
        monkeypatch.setattr(SitePhoto._meta.get_field(field), "storage", storage)
    original = BytesIO()
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (800, 400), "red").save(original, format="JPEG", exif=exif)
    return actor, site, storage, original.getvalue()


def upload_one(setup_upload):
    actor, site, _, data = setup_upload
    return upload_site_photo(actor=actor, site=site, upload=SimpleUploadedFile("original.jpg", data))


class MirrorSource:
    is_configured = True

    def __init__(self, site):
        self.folder = f"DLC Montage/AC/{site.group.name}/{site.project_number} - {site.name}/Fotos"
        self.files = {}
        self.fail = None

    def list_folder(self, folder):
        return (
            [{"name": path.rsplit("/", 1)[-1], "relative_path": path, "etag": "revision1"} for path in self.files]
            if folder == self.folder
            else []
        )

    def ensure_folder(self, folder):
        assert folder == self.folder
        return True

    def put_file(self, path, data, *, content_type):
        assert content_type == "image/jpeg"
        if self.fail:
            raise self.fail
        if path in self.files:
            raise NextcloudUploadConflict("exists")
        self.files[path] = data
        return "revision1"

    def get_file(self, path, **kwargs):
        return self.files[path], "image/jpeg"


def test_upload_preserves_full_exif_and_makes_oriented_thumbnail(setup_upload):
    _, _, storage, data = setup_upload
    with patch("features.project_media.photo_uploads.NextcloudWebDAVClient") as cloud:
        photo = upload_one(setup_upload)
    cloud.assert_not_called()
    assert storage.open(photo.image.name).read() == data
    assert photo.checksum == sha256(data).hexdigest()
    assert photo.mirror_status == "queued"
    assert photo.source_kind == "uploaded"
    summary = get_site_photo_summary(photo.site)
    assert summary["mirror_pending"] is True
    assert summary["sync_status"] == "mirroring"
    with Image.open(storage.open(photo.thumbnail.name)) as preview:
        assert preview.format == "WEBP"
        assert preview.size == (240, 480)
    with Image.open(storage.open(photo.image.name)) as full:
        assert full.getexif()[274] == 6


def test_customer_and_inactive_actor_cannot_upload(setup_upload):
    actor, site, _, data = setup_upload
    customer = get_user_model().objects.create_user(username="customer-emil")
    from features.customer_portal.models import ClientMembership
    from features.projects.models import Client

    client = Client.objects.create(name="Client")
    ClientMembership.objects.create(user=customer, client=client, can_manage_projects=True, granted_by=actor)
    assert not can_upload_site_photos(customer, site)
    with pytest.raises(PermissionDenied):
        upload_site_photo(actor=customer, site=site, upload=SimpleUploadedFile("a.jpg", data))
    actor.is_active = False
    assert not can_upload_site_photos(actor, site)


def test_thumbnail_storage_failure_removes_new_original(setup_upload, monkeypatch):
    _, _, storage, _ = setup_upload
    saved = []
    original_save = storage.save

    def save(name, content, *args, **kwargs):
        if name.endswith(".webp"):
            raise OSError("preview write failed")
        result = original_save(name, content, *args, **kwargs)
        saved.append(result)
        return result

    monkeypatch.setattr(storage, "save", save)
    with pytest.raises(OSError):
        upload_one(setup_upload)
    assert SitePhoto.objects.count() == 0
    assert saved and not storage.exists(saved[0])


def test_lost_storage_save_response_cleans_our_opaque_key(setup_upload, monkeypatch):
    _, _, storage, _ = setup_upload
    original_save = storage.save
    saved = []

    def lost_response(name, content, *args, **kwargs):
        saved.append(original_save(name, content, *args, **kwargs))
        raise OSError("save response lost after write")

    monkeypatch.setattr(storage, "save", lost_response)
    with pytest.raises(OSError):
        upload_one(setup_upload)
    assert SitePhoto.objects.count() == 0
    assert saved and not storage.exists(saved[0])


def test_mirror_full_only_and_inbound_listing_does_not_duplicate(setup_upload):
    _, site, _, data = setup_upload
    photo = upload_one(setup_upload)
    source = MirrorSource(site)
    assert mirror_site_photo(photo, client=source) == "ok"
    photo.refresh_from_db()
    assert source.files[photo.source_path] == data
    assert photo.source_id == sha256(photo.source_path.encode()).hexdigest()
    assert sync_site_photos(site, client=source, force=True).unchanged == 1
    assert get_site_photo_summary(site)["mirror_pending"] is False
    assert SitePhoto.objects.count() == 1
    assert mirror_site_photo(photo, client=source) == "ok"
    assert len(source.files) == 1


def test_removed_remote_folder_is_not_recreated_until_a_new_upload(setup_upload, monkeypatch):
    _, site, storage, data = setup_upload
    first = upload_one(setup_upload)
    source = MirrorSource(site)
    source.ensure_folder = Mock(return_value=True)
    monkeypatch.setattr("features.project_media.photo_uploads.NextcloudWebDAVClient", lambda **kwargs: source)
    assert process_pending_photo_mirrors() == 1
    first.refresh_from_db()
    assert first.mirror_status == "ok"
    source.files.clear()  # Customer takes the files and removes the remote folder.
    source.ensure_folder.reset_mock()

    assert sync_site_photos(site, client=source, force=True).synced == 0
    assert process_pending_photo_mirrors() == 0
    source.ensure_folder.assert_not_called()
    assert storage.open(first.image.name).read() == data
    assert storage.exists(first.thumbnail.name)

    second = upload_one(setup_upload)  # A new upload explicitly allows folder creation.
    source.ensure_folder.assert_not_called()
    assert process_pending_photo_mirrors() == 1
    source.ensure_folder.assert_called_once_with(source.folder)
    second.refresh_from_db()
    assert second.mirror_status == "ok"
    assert source.files == {second.source_path: data}
    assert SitePhoto.objects.count() == 2


def test_worker_failure_preserves_s3_and_has_bounded_retries(setup_upload, monkeypatch):
    _, site, storage, data = setup_upload
    photo = upload_one(setup_upload)
    source = MirrorSource(site)
    source.fail = NextcloudWebDAVError("temporary")
    monkeypatch.setattr("features.project_media.photo_uploads.NextcloudWebDAVClient", lambda **kwargs: source)
    for attempt in range(1, 4):
        SitePhoto.objects.filter(pk=photo.pk).update(mirror_next_attempt_at=timezone.now())
        assert process_pending_photo_mirrors() == 1
        photo.refresh_from_db()
        assert photo.mirror_attempts == attempt
        assert storage.open(photo.image.name).read() == data
    assert photo.mirror_status == "failed"
    assert process_pending_photo_mirrors() == 0


def test_auth_failure_is_not_retried(setup_upload, monkeypatch):
    _, site, _, _ = setup_upload
    photo = upload_one(setup_upload)
    source = MirrorSource(site)
    source.fail = NextcloudUploadPermanentError("denied")
    monkeypatch.setattr("features.project_media.photo_uploads.NextcloudWebDAVClient", lambda **kwargs: source)
    assert process_pending_photo_mirrors() == 1
    photo.refresh_from_db()
    assert photo.mirror_status == "failed"
    assert photo.mirror_attempts == 1


def test_conflicting_remote_content_is_not_overwritten(setup_upload):
    _, site, _, _ = setup_upload
    photo = upload_one(setup_upload)
    source = MirrorSource(site)
    path = f"{source.folder}/{photo.remote_name}"
    source.files[path] = b"foreign-file"
    with pytest.raises(NextcloudUploadPermanentError):
        mirror_site_photo(photo, client=source)
    assert source.files[path] == b"foreign-file"


def test_lost_put_response_retries_without_duplicate_photo(setup_upload, monkeypatch):
    _, site, _, _ = setup_upload
    photo = upload_one(setup_upload)
    source = MirrorSource(site)
    put = source.put_file
    first = True

    def lose_first_response(path, data, *, content_type):
        nonlocal first
        result = put(path, data, content_type=content_type)
        if first:
            first = False
            raise NextcloudWebDAVError("response lost after remote write")
        return result

    source.put_file = lose_first_response
    monkeypatch.setattr("features.project_media.photo_uploads.NextcloudWebDAVClient", lambda **kwargs: source)
    assert process_pending_photo_mirrors() == 1
    photo.refresh_from_db()
    assert photo.mirror_status == "queued"
    assert sync_site_photos(site, client=source, force=True).unchanged == 1
    SitePhoto.objects.filter(pk=photo.pk).update(mirror_next_attempt_at=timezone.now())
    assert process_pending_photo_mirrors() == 1
    photo.refresh_from_db()
    assert photo.mirror_status == "ok"
    assert len(source.files) == SitePhoto.objects.count() == 1


def test_put_is_conditional_and_rejects_redirects():
    client = NextcloudWebDAVClient(base_url="https://cloud.test/remote.php/dav/files/DLC/")
    response = Mock(status_code=302)
    with patch("features.integrations.nextcloud.client.requests.put", return_value=response) as request:
        with pytest.raises(NextcloudUploadPermanentError):
            client.put_file("Fotos/opaque.jpg", b"content", content_type="image/jpeg")
    assert request.call_args.kwargs["allow_redirects"] is False
    assert request.call_args.kwargs["headers"]["If-None-Match"] == "*"
    response.close.assert_called_once()

def test_sequential_upload_json_saves_original_and_queues_mirror(setup_upload, client, monkeypatch):
    from django.urls import reverse
    actor, site, storage, data = setup_upload
    monkeypatch.setattr('features.integrations.nextcloud.client.NextcloudWebDAVClient.put_file',
                        lambda *a, **k: pytest.fail('Nextcloud must remain background-only'))
    client.force_login(actor)
    response = client.post(reverse('site_photos:upload', args=[site.pk]),
        {'photos': SimpleUploadedFile('original.jpg', data)}, HTTP_ACCEPT='application/json')
    assert response.status_code == 200
    result = response.json()
    assert result['errors'] == []
    assert len(result['uploaded']) == 1
    photo = SitePhoto.objects.get(pk=result['uploaded'][0]['id'])
    assert storage.open(photo.image.name).read() == data
    assert photo.mirror_status == 'queued'
    assert response['Cache-Control'] == 'private, no-store'


def test_sequential_upload_json_validation_failure_has_no_storage_writes(setup_upload, client):
    from django.urls import reverse
    actor, site, _, _ = setup_upload
    client.force_login(actor)
    response = client.post(reverse('site_photos:upload', args=[site.pk]),
        {'photos': SimpleUploadedFile('broken.png', b'invalid')}, HTTP_ACCEPT='application/json')
    assert response.status_code == 400
    assert response.json()['uploaded'] == []
    assert response.json()['errors']
    assert SitePhoto.objects.count() == 0
