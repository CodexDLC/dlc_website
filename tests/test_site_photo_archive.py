"""ZIP exports preserve original bytes and remain scoped to one authorized site."""

from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.urls import reverse
from features.project_media.models import SitePhoto
from features.project_media.photo_exports import build_photo_archive
from features.projects.models import AcObject, ProjectGroup

pytestmark = pytest.mark.django_db


@pytest.fixture
def archive_setup(tmp_path, monkeypatch, django_user_model, settings):
    settings.PHOTOS_STORAGE_BACKEND = "local"
    monkeypatch.setattr(SitePhoto._meta.get_field("image"), "storage", FileSystemStorage(location=tmp_path))
    actor = django_user_model.objects.create_superuser(username="archive-admin", password=None)
    group = ProjectGroup.objects.create(name="Archive group")
    site = AcObject.objects.create(group=group, name="Archive site")
    other = AcObject.objects.create(group=group, name="Other site")
    originals = {}
    for item, content in [(site, b"full-original-bytes"), (other, b"foreign-original-bytes")]:
        photo = SitePhoto.objects.create(
            site=item,
            source_id=str(item.pk),
            source_path=f"source/{item.pk}/photo.jpg",
            original_name="../../original.jpg",
            checksum=sha256(content).hexdigest(),
            content_type="image/jpeg",
            size=len(content),
            image=ContentFile(content, name="original.jpg"),
        )
        originals[item.pk] = photo
    return actor, site, other, originals


def test_archive_contains_only_own_original_bytes_and_safe_names(archive_setup, monkeypatch):
    _, site, _, _ = archive_setup
    monkeypatch.setattr(
        "features.integrations.nextcloud.client.NextcloudWebDAVClient.get_file",
        lambda *a, **k: pytest.fail("No Nextcloud for ZIP"),
    )
    with build_photo_archive(site) as output, ZipFile(output) as archive:
        assert len(archive.namelist()) == 1
        name = archive.namelist()[0]
        assert "/" not in name and "\\" not in name
        assert archive.read(name) == b"full-original-bytes"


def test_archive_attachment_and_original_download(archive_setup, client):
    actor, site, _, originals = archive_setup
    client.force_login(actor)
    response = client.get(reverse("site_photos:archive", args=[site.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert response["Content-Disposition"].startswith("attachment;")
    with ZipFile(BytesIO(b"".join(response.streaming_content))) as archive:
        assert archive.read(archive.namelist()[0]) == b"full-original-bytes"
    response = client.get(reverse("site_photos:image", args=[site.pk, originals[site.pk].pk]), {"download": "1"})
    assert response["Content-Disposition"].startswith("attachment;")
    assert b"".join(response.streaming_content) == b"full-original-bytes"


def test_archive_limits_and_empty_site_are_rejected(archive_setup):
    _, site, _, originals = archive_setup
    photo = originals[site.pk]
    SitePhoto.objects.filter(pk=photo.pk).update(size=101 * 1024 * 1024)
    with pytest.raises(ValidationError):
        build_photo_archive(site)
    SitePhoto.objects.filter(pk=photo.pk).delete()
    with pytest.raises(ValidationError):
        build_photo_archive(site)


def test_photo_upload_rejects_oversized_batch_before_storage():
    from django.core.files.uploadedfile import SimpleUploadedFile
    from features.project_media.photo_forms import PhotoUploadForm

    photos = [SimpleUploadedFile(f"photo-{index}.png", b"placeholder") for index in range(6)]
    for photo in photos:
        photo.size = 19 * 1024 * 1024
    form = PhotoUploadForm(data={}, files={"photos": photos})
    assert not form.is_valid()
    assert "100" in str(form.errors["photos"])
