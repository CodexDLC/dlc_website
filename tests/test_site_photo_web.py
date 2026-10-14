"""Saved site photos stay independent of remote I/O and enforce site permissions."""

from hashlib import sha256
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client as DjangoClient
from django.urls import reverse
from features.customer_portal.services import grant_membership
from features.project_media.models import SitePhoto, SitePhotoSyncState
from features.project_media.photo_forms import PhotoUploadForm
from features.projects.models import AcObject, Client, ProjectGroup
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture
def saved_photo_setup(tmp_path, monkeypatch, settings):
    settings.PHOTOS_STORAGE_BACKEND = "local"
    storage = FileSystemStorage(location=tmp_path)
    monkeypatch.setattr(SitePhoto._meta.get_field("image"), "storage", storage)
    monkeypatch.setattr(SitePhoto._meta.get_field("thumbnail"), "storage", storage)
    users = get_user_model()
    manager = users.objects.create_superuser(username="saved-admin", email="admin@example.test", password=None)
    owner = users.objects.create_user(username="saved-owner")
    outsider = users.objects.create_user(username="saved-outsider")
    customer = Client.objects.create(name="Photo owner")
    foreign = Client.objects.create(name="Other owner")
    grant_membership(actor=manager, user=owner, client=customer)
    grant_membership(actor=manager, user=outsider, client=foreign)
    group = ProjectGroup.objects.create(name="Photo group", client=customer)
    site = AcObject.objects.create(group=group, name="Photo site")
    content = BytesIO()
    Image.new("RGB", (2, 2), "green").save(content, format="PNG")
    png = content.getvalue()
    photo = SitePhoto.objects.create(
        site=site, source_id="source-1", source_path="private/roof.png",
        checksum=sha256(png).hexdigest(), image=ContentFile(png, name="roof.png"),
        thumbnail=ContentFile(png, name="roof-thumb.png"), thumbnail_content_type="image/png",
        original_name="roof.png", content_type="image/png", size=len(png),
    )
    return manager, owner, outsider, site, photo


def forbid_remote(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("HTTP photo flow must never contact Nextcloud")

    monkeypatch.setattr("features.integrations.nextcloud.services.get_site_folder_path", fail)
    monkeypatch.setattr("features.integrations.nextcloud.client.NextcloudWebDAVClient.list_folder", fail)
    monkeypatch.setattr("features.integrations.nextcloud.client.NextcloudWebDAVClient.get_file", fail)


@pytest.mark.parametrize("internal", [False, True])
@pytest.mark.parametrize("language,show,hide", [
    ("ru", "Показать фотографии", "Скрыть фотографии"),
    ("de", "Fotos anzeigen", "Fotos ausblenden"),
])
def test_site_pages_show_saved_photos_without_remote_io(
    saved_photo_setup, client, monkeypatch, internal, language, show, hide,
):
    manager, owner, _, site, photo = saved_photo_setup
    forbid_remote(monkeypatch)
    client.force_login(manager if internal else owner)
    from django.utils.translation import override

    with override(language):
        url = (
            reverse("projects:site_detail", args=[site.group_id, site.pk])
            if internal else reverse("customer_portal:site", args=[site.pk])
        )
        response = client.get(url, HTTP_ACCEPT_LANGUAGE=language)
        assert response.status_code == 200
        content = response.content.decode()
        assert "📸 1" in content
        assert show in content
        assert "roof.png" not in content
        assert reverse("site_photos:image", args=[site.pk, photo.pk]) not in content
        assert "site_photos.js" in content
        upload_url = reverse("site_photos:upload", args=[site.pk])
        assert (upload_url in content) is internal
        assert reverse("site_photos:archive", args=[site.pk]) in content
        assert not SitePhotoSyncState.objects.filter(site=site).exists()
        expanded = client.get(url, {"show_photos": "1"}, HTTP_ACCEPT_LANGUAGE=language)
        assert expanded.status_code == 200
        assert hide in expanded.content.decode()
        assert reverse("site_photos:image", args=[site.pk, photo.pk]) in expanded.content.decode()
        assert '<img src="' + reverse("site_photos:thumbnail", args=[site.pk, photo.pk]) in expanded.content.decode()
        full_image_src = '<img src="' + reverse("site_photos:image", args=[site.pk, photo.pk]) + "?"
        assert full_image_src not in expanded.content.decode()


def test_gallery_get_is_read_only_and_saved_images_survive_failure(saved_photo_setup, client, monkeypatch):
    _, owner, _, site, photo = saved_photo_setup
    forbid_remote(monkeypatch)
    SitePhotoSyncState.objects.create(site=site, source_context="test", status="unavailable")
    client.force_login(owner)
    response = client.get(reverse("site_photos:gallery", args=[site.pk]), {"show_photos": "1"})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["status"] == "unavailable"
    assert "roof.png" in data["html"]
    assert reverse("site_photos:image", args=[site.pk, photo.pk]) in data["html"]
    assert SitePhotoSyncState.objects.get(site=site).status == "unavailable"


@pytest.mark.parametrize("endpoint", ["gallery", "refresh", "image", "thumbnail", "archive", "upload"])
def test_foreign_customer_cannot_access_photos(saved_photo_setup, client, endpoint):
    _, _, outsider, site, photo = saved_photo_setup
    client.force_login(outsider)
    args = [site.pk, photo.pk] if endpoint in {"image", "thumbnail"} else [site.pk]
    url = reverse(f"site_photos:{endpoint}", args=args)
    response = client.post(url) if endpoint == "refresh" else client.get(url)
    assert response.status_code == 403
    assert not SitePhotoSyncState.objects.filter(site=site).exists()


def test_read_only_customer_cannot_upload(saved_photo_setup, client):
    _, owner, _, site, _ = saved_photo_setup
    client.force_login(owner)
    url = reverse("site_photos:upload", args=[site.pk])
    assert client.get(url).status_code == 403
    assert client.post(url).status_code == 403


def test_upload_page_uses_multiple_file_field_for_internal_manager(saved_photo_setup, client):
    manager, _, _, site, _ = saved_photo_setup
    client.force_login(manager)
    response = client.get(reverse("site_photos:upload", args=[site.pk]))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'enctype="multipart/form-data"' in content
    assert 'name="photos"' in content
    assert "multiple" in content
    assert "csrfmiddlewaretoken" in content


def test_mirror_status_is_visible_only_to_uploaders(saved_photo_setup, client):
    manager, owner, _, site, photo = saved_photo_setup
    SitePhoto.objects.filter(pk=photo.pk).update(mirror_status="queued")
    url = reverse("site_photos:gallery", args=[site.pk])
    client.force_login(owner)
    customer_html = client.get(url, {"show_photos": "1"}).json()["html"]
    assert "data-photo-mirror" not in customer_html
    client.force_login(manager)
    staff_html = client.get(url, {"show_photos": "1"}).json()["html"]
    assert "data-photo-mirror" in staff_html
    assert "Nextcloud" in staff_html


def test_authorized_image_reads_saved_file(saved_photo_setup, client, monkeypatch):
    _, owner, _, site, photo = saved_photo_setup
    forbid_remote(monkeypatch)
    client.force_login(owner)
    response = client.get(reverse("site_photos:image", args=[site.pk, photo.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")


def test_photo_id_is_scoped_to_authorized_site(saved_photo_setup, client):
    _, owner, _, site, photo = saved_photo_setup
    second_site = AcObject.objects.create(group=site.group, name="Other accessible site")
    client.force_login(owner)
    response = client.get(reverse("site_photos:image", args=[second_site.pk, photo.pk]))
    assert response.status_code == 404


def test_s3_image_redirect_uses_authorized_private_url(saved_photo_setup, client, settings, monkeypatch):
    _, owner, _, site, photo = saved_photo_setup
    settings.PHOTOS_STORAGE_BACKEND = "s3"
    forbid_remote(monkeypatch)
    monkeypatch.setattr(photo.image.storage, "url", lambda name: "https://private-storage.example.test/signed?signature=fixture")
    client.force_login(owner)
    response = client.get(reverse("site_photos:image", args=[site.pk, photo.pk]))
    assert response.status_code == 302
    assert response["Location"] == "https://private-storage.example.test/signed?signature=fixture"
    assert response["Cache-Control"] == "private, no-store"


def test_refresh_requires_csrf_and_only_enqueues(saved_photo_setup, monkeypatch):
    _, owner, _, site, _ = saved_photo_setup
    forbid_remote(monkeypatch)
    client = DjangoClient(enforce_csrf_checks=True)
    client.force_login(owner)
    refresh_url = reverse("site_photos:refresh", args=[site.pk])
    assert client.post(refresh_url).status_code == 403
    assert not SitePhotoSyncState.objects.filter(site=site).exists()
    assert client.get(reverse("site_photos:gallery", args=[site.pk])).status_code == 200
    assert not SitePhotoSyncState.objects.filter(site=site).exists()
    response = client.post(refresh_url, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert SitePhotoSyncState.objects.get(site=site).status == "queued"


def test_upload_form_validates_entire_batch_before_storage():
    content = BytesIO()
    Image.new("RGB", (2, 2), "green").save(content, format="PNG")
    good = SimpleUploadedFile("good.png", content.getvalue(), content_type="image/png")
    bad = SimpleUploadedFile("bad.png", b"broken", content_type="image/png")
    form = PhotoUploadForm(files={"photos": [good, bad]})
    assert not form.is_valid()
    assert "bad.png" in str(form.errors)
    assert not SitePhoto.objects.exists()
    assert good.tell() == 0


def test_upload_form_rejects_empty_and_more_than_twenty_photos():
    assert not PhotoUploadForm(files={}).is_valid()
    photos = [SimpleUploadedFile(f"{index}.png", b"fixture") for index in range(21)]
    form = PhotoUploadForm(files={"photos": photos})
    assert not form.is_valid()
    assert "20" in str(form.errors)


def test_upload_form_returns_all_valid_images():
    content = BytesIO()
    Image.new("RGB", (2, 2), "green").save(content, format="PNG")
    photos = [SimpleUploadedFile(f"{index}.png", content.getvalue(), content_type="image/png") for index in range(2)]
    form = PhotoUploadForm(files={"photos": photos})
    assert form.is_valid(), form.errors
    assert form.cleaned_data["photos"] == photos

