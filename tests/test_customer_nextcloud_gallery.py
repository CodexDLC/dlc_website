"""Тесты защищённой фотогалереи Nextcloud в кабинете заказчика."""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from features.customer_portal.exports import group_workbook, site_workbook
from features.customer_portal.models import ClientMembership
from features.customer_portal.selectors import customer_site_detail, get_cached_photo_summary
from features.customer_portal.services import grant_membership
from features.integrations.nextcloud.client import NextcloudWebDAVClient, NextcloudWebDAVError
from features.integrations.nextcloud.services import (
    fetch_site_photo,
    get_site_photo_cache_key,
    get_site_photo_summary,
    validate_image_bytes,
)
from features.projects.models import AcObject, Client, ProjectGroup

pytestmark = pytest.mark.django_db

# Минимальные валидные байты изображений
VALID_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"
VALID_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
VALID_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x30\x01\x00\x9d\x01\x2a\x01\x00\x01\x00\x02\x00\x34\x25"


@pytest.fixture
def portal_setup():
    cache.clear()
    users = get_user_model()
    manager = users.objects.create_superuser(username="gal-admin", email="admin@example.test", password=None)
    alice = users.objects.create_user(username="gal-alice")
    bob = users.objects.create_user(username="gal-bob")
    client_a = Client.objects.create(name="Auftraggeber Alpha")
    client_b = Client.objects.create(name="Auftraggeber Beta")

    grant_membership(actor=manager, user=alice, client=client_a, can_manage_projects=True)
    grant_membership(actor=manager, user=bob, client=client_b, can_manage_projects=False)

    group_a = ProjectGroup.objects.create(name="Anlage Alpha", client=client_a)
    group_b = ProjectGroup.objects.create(name="Anlage Beta", client=client_b)

    site_a = AcObject.objects.create(group=group_a, name="Haus Alpha 1", project_number="2026-101")
    site_b = AcObject.objects.create(group=group_b, name="Haus Beta 1", project_number="2026-201")

    return {
        "manager": manager,
        "alice": alice,
        "bob": bob,
        "client_a": client_a,
        "client_b": client_b,
        "group_a": group_a,
        "group_b": group_b,
        "site_a": site_a,
        "site_b": site_b,
    }


# ---------------------------------------------------------------------------
# 1. Тесты клиента WebDAV (_full_url, get_file, list_folder)
# ---------------------------------------------------------------------------


def test_client_full_url_collection_and_file():
    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    # Коллекция обязательно имеет завершающий слеш
    assert (
        client._full_url("Fotos", is_collection=True)
        == "https://storage.test/remote.php/dav/files/user/Fotos/"
    )
    # Файл НЕ должен иметь завершающего слеша
    assert (
        client._full_url("Fotos/image.jpg", is_collection=False)
        == "https://storage.test/remote.php/dav/files/user/Fotos/image.jpg"
    )
    # Корневой URL
    assert client._full_url("", is_collection=True) == "https://storage.test/remote.php/dav/files/user/"


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_list_folder_http_failure_raises(mock_request):
    """Сбой HTTP (500) выбрасывает исключение NextcloudWebDAVError, а не скрывается пустым списком."""
    resp = MagicMock()
    resp.status_code = 500
    mock_request.return_value = resp

    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    with pytest.raises(NextcloudWebDAVError) as exc_info:
        client.list_folder("Fotos")
    assert "status 500" in str(exc_info.value)


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_list_folder_not_found_returns_empty(mock_request):
    """Если папка ещё не создана (404), list_folder возвращает пустой список."""
    resp = MagicMock()
    resp.status_code = 404
    mock_request.return_value = resp

    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    items = client.list_folder("Fotos")
    assert items == []


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_list_folder_filters_hostile_and_traversal_hrefs(mock_request):
    """Hostile DAV hrefs (с выходом за пределы пути или чужого пользователя) отфильтровываются."""
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
    <d:response>
        <d:href>/remote.php/dav/files/DLC/Fotos/</d:href>
        <d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop></d:propstat>
    </d:response>
    <d:response>
        <d:href>/remote.php/dav/files/DLC/Fotos/valid.jpg</d:href>
        <d:propstat><d:prop><d:resourcetype/></d:prop></d:propstat>
    </d:response>
    <d:response>
        <d:href>/remote.php/dav/files/other_user/secret.jpg</d:href>
        <d:propstat><d:prop><d:resourcetype/></d:prop></d:propstat>
    </d:response>
    <d:response>
        <d:href>/remote.php/dav/files/DLC/Fotos/../../passwords.txt</d:href>
        <d:propstat><d:prop><d:resourcetype/></d:prop></d:propstat>
    </d:response>
    <d:response>
        <d:href>/remote.php/dav/files/DLC/OtherFolder/other.jpg</d:href>
        <d:propstat><d:prop><d:resourcetype/></d:prop></d:propstat>
    </d:response>
</d:multistatus>"""
    resp = MagicMock()
    resp.status_code = 207
    resp.text = xml_data
    mock_request.return_value = resp

    client = NextcloudWebDAVClient(
        base_url="https://storage.test/remote.php/dav/files/DLC/", username="DLC"
    )
    items = client.list_folder("Fotos")
    assert len(items) == 1
    assert items[0]["name"] == "valid.jpg"


@patch("features.integrations.nextcloud.client.requests.get")
def test_client_get_file_redirect_rejected(mock_get):
    """Редиректы с WebDAV сервера категорически отклоняются и поток закрывается."""
    resp = MagicMock()
    resp.is_redirect = True
    resp.status_code = 302
    mock_get.return_value = resp

    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    with pytest.raises(NextcloudWebDAVError) as exc_info:
        client.get_file("Fotos/photo.jpg")
    assert "Redirect rejected" in str(exc_info.value)
    resp.close.assert_called_once()


@patch("features.integrations.nextcloud.client.requests.get")
def test_client_get_file_excessive_payload_rejected(mock_get):
    """Слишком большой файл (превышающий max_size) отклоняется и поток закрывается."""
    resp = MagicMock()
    resp.is_redirect = False
    resp.status_code = 200
    resp.headers = {"Content-Length": "30000000"}  # 30 MB
    mock_get.return_value = resp

    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    with pytest.raises(NextcloudWebDAVError) as exc_info:
        client.get_file("Fotos/huge.jpg", max_size=20 * 1024 * 1024)
    assert "exceeds maximum allowed" in str(exc_info.value)
    resp.close.assert_called_once()


@patch("features.integrations.nextcloud.client.requests.get")
def test_client_get_file_stream_closed_on_success(mock_get):
    """При успешном чтении GET поток закрывается в блоке finally."""
    resp = MagicMock()
    resp.is_redirect = False
    resp.status_code = 200
    resp.headers = {"Content-Length": "3", "Content-Type": "image/jpeg"}
    resp.iter_content.return_value = [b"xyz"]
    mock_get.return_value = resp

    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    data, content_type = client.get_file("Fotos/small.jpg")
    assert data == b"xyz"
    assert content_type == "image/jpeg"
    resp.close.assert_called_once()


@patch("features.integrations.nextcloud.client.requests.get")
def test_client_get_file_stream_closed_on_http_error(mock_get):
    """При ошибке HTTP (500) поток закрывается в блоке finally."""
    resp = MagicMock()
    resp.is_redirect = False
    resp.status_code = 500
    mock_get.return_value = resp

    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    with pytest.raises(NextcloudWebDAVError):
        client.get_file("Fotos/error.jpg")
    resp.close.assert_called_once()


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_propfind_redirect_rejected_and_closed(mock_request):
    """PROPFIND отклоняет редирект (allow_redirects=False) и закрывает ответ."""
    resp = MagicMock()
    resp.is_redirect = True
    resp.status_code = 301
    mock_request.return_value = resp

    client = NextcloudWebDAVClient(base_url="https://storage.test/remote.php/dav/files/user/")
    with pytest.raises(NextcloudWebDAVError) as exc_info:
        client.list_folder("Fotos")
    assert "Redirect rejected" in str(exc_info.value)
    mock_request.assert_called_once()
    assert mock_request.call_args.kwargs.get("allow_redirects") is False
    resp.close.assert_called_once()


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_propfind_redirect_classified_as_unavailable(mock_request, portal_setup, settings):
    """Редирект в PROPFIND классифицируется get_site_photo_summary как статус unavailable."""
    site = portal_setup["site_a"]
    settings.NEXTCLOUD_WEBDAV_URL = "https://storage.test/remote.php/dav/files/user/"
    settings.NEXTCLOUD_USER = "test-user"
    settings.NEXTCLOUD_PASSWORD = "synthetic-test-password"  # noqa: S105 - synthetic fixture only
    cache.clear()
    resp = MagicMock()
    resp.is_redirect = True
    resp.status_code = 302
    mock_request.return_value = resp

    summary = get_site_photo_summary(site)
    assert summary["status"] == "unavailable"
    assert summary["is_available"] is False
    assert "Redirect rejected" in summary["error"]


# ---------------------------------------------------------------------------
# 2. Сервисные проверки: валидация байтов, сводка, фото
# ---------------------------------------------------------------------------


def test_validate_image_bytes():
    assert validate_image_bytes(VALID_JPEG, ".jpg") == "image/jpeg"
    assert validate_image_bytes(VALID_PNG, ".png") == "image/png"
    assert validate_image_bytes(VALID_WEBP, ".webp") == "image/webp"

    # SVG и HTML категорически отклоняются
    with pytest.raises(ValueError, match="HTML or XML/SVG"):
        validate_image_bytes(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>", ".jpg")

    with pytest.raises(ValueError, match="HTML or XML/SVG"):
        validate_image_bytes(b"<!DOCTYPE html><html><body>attack</body></html>", ".png")

    # Некорректные сигнатуры
    with pytest.raises(ValueError, match="Invalid JPEG magic bytes"):
        validate_image_bytes(b"NOT_A_JPEG_STREAM", ".jpg")


def test_get_site_photo_summary_unavailable_vs_empty(portal_setup):
    site = portal_setup["site_a"]

    # 1. Пустой список фото: статус 'ok', count=0, is_available=True
    cache.clear()
    mock_client = MagicMock()
    mock_client.list_folder.return_value = []
    summary_empty = get_site_photo_summary(site, client=mock_client)
    assert summary_empty["status"] == "ok"
    assert summary_empty["is_available"] is True
    assert summary_empty["has_photos"] is False
    assert summary_empty["count"] == 0

    # 2. Ошибка облака (500 / Network Error): статус 'unavailable', count=0, is_available=False
    cache.clear()
    mock_client.list_folder.side_effect = NextcloudWebDAVError("Nextcloud down")
    summary_err = get_site_photo_summary(site, client=mock_client)
    assert summary_err["status"] == "unavailable"
    assert summary_err["is_available"] is False
    assert summary_err["has_photos"] is False
    assert summary_err["count"] == 0
    assert "Nextcloud down" in summary_err["error"]


def test_fetch_site_photo_guards(portal_setup):
    site = portal_setup["site_a"]
    cache.clear()

    # Traversal в имени файла
    with pytest.raises(ValueError, match="Invalid photo filename"):
        fetch_site_photo(site, "../secret.jpg")

    with pytest.raises(ValueError, match="Invalid photo filename"):
        fetch_site_photo(site, "sub/photo.jpg")

    # Файл HEIC учитывается в сумме, но не в preview
    mock_client = MagicMock()
    mock_client.list_folder.return_value = [
        {"name": "photo.heic", "is_directory": False},
        {"name": "photo.jpg", "is_directory": False},
    ]
    summary = get_site_photo_summary(site, client=mock_client)
    assert summary["count"] == 2
    heic_entry = next(p for p in summary["photos"] if p["name"] == "photo.heic")
    assert heic_entry["is_previewable"] is False

    # Запрос HEIC через fetch_site_photo отклоняется
    with pytest.raises(ValueError, match="not supported for safe browser preview"):
        fetch_site_photo(site, "photo.heic", client=mock_client)

    # Запрос файла, отсутствующего в листинге папки
    with pytest.raises(FileNotFoundError, match="not listed in site photos"):
        fetch_site_photo(site, "unlisted.jpg", client=mock_client)


# ---------------------------------------------------------------------------
# 3. HTTP View тесты: права доступа, изоляция, безопасный прокси
# ---------------------------------------------------------------------------


@patch("features.integrations.nextcloud.services.NextcloudWebDAVClient")
def test_customer_photo_proxy_own_client_success(mock_client_cls, portal_setup, client):
    """Свой пользователь (Alice) получает фото через безопасный прокси."""
    alice = portal_setup["alice"]
    site_a = portal_setup["site_a"]

    mock_client = mock_client_cls.return_value
    mock_client.list_folder.return_value = [
        {"name": "roof.jpg", "is_directory": False},
    ]
    mock_client.get_file.return_value = (VALID_JPEG, "image/jpeg")

    client.force_login(alice)
    url = reverse("customer_portal:site_photo", kwargs={"site_id": site_a.pk, "filename": "roof.jpg"})
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "image/jpeg"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert "sandbox" in response["Content-Security-Policy"]
    assert response["Cache-Control"] == "private, no-store"
    assert response.content == VALID_JPEG

    # Проверка, что в ответе нет паролей или приватных URL хранилища
    assert b"password" not in response.content.lower()
    assert "authorization" not in response.headers


def test_customer_photo_proxy_foreign_client_denied(portal_setup, client):
    """Чужой заказчик (Bob) не имеет доступа к фото объекта Alice."""
    bob = portal_setup["bob"]
    site_a = portal_setup["site_a"]

    client.force_login(bob)
    url = reverse("customer_portal:site_photo", kwargs={"site_id": site_a.pk, "filename": "roof.jpg"})
    response = client.get(url)
    assert response.status_code == 404


def test_customer_photo_proxy_inactive_user_denied(portal_setup, client):
    """Неактивный пользователь или отозванное членство не могут смотреть фото."""
    alice = portal_setup["alice"]
    site_a = portal_setup["site_a"]

    ClientMembership.objects.filter(user=alice).update(is_active=False)
    client.force_login(alice)
    url = reverse("customer_portal:site_photo", kwargs={"site_id": site_a.pk, "filename": "roof.jpg"})
    response = client.get(url)
    assert response.status_code == 403


def test_customer_photo_proxy_unauthenticated_redirects(portal_setup, client):
    """Неавторизованный пользователь перенаправляется на логин."""
    site_a = portal_setup["site_a"]
    url = reverse("customer_portal:site_photo", kwargs={"site_id": site_a.pk, "filename": "roof.jpg"})
    response = client.get(url)
    assert response.status_code == 302


@patch("features.integrations.nextcloud.services.NextcloudWebDAVClient")
@pytest.mark.parametrize("internal", [False, True])
@pytest.mark.parametrize("language,show_label,hide_label", [
    ("ru", "Показать фотографии", "Скрыть фотографии"),
    ("de", "Fotos anzeigen", "Fotos ausblenden"),
])
def test_site_photos_are_revealed_on_request(
    mock_client_cls, portal_setup, client, internal, language, show_label, hide_label
):
    """Both site pages show a count first and request private previews only after Show."""
    alice = portal_setup["alice"]
    site_a = portal_setup["site_a"]

    mock_client = mock_client_cls.return_value
    mock_client.list_folder.return_value = [
        {"name": "overview.jpg", "is_directory": False},
        {"name": "inverter.png", "is_directory": False},
    ]

    from django.utils.translation import override

    client.force_login(portal_setup["manager"] if internal else alice)
    with override(language):
        url = (
            reverse("projects:site_detail", kwargs={"group_id": site_a.group_id, "pk": site_a.pk})
            if internal else reverse("customer_portal:site", kwargs={"site_id": site_a.pk})
        )
        response = client.get(url, {"date": "2026-10-09"}, HTTP_ACCEPT_LANGUAGE=language)
        assert response.status_code == 200
        collapsed = response.content.decode("utf-8")
        assert "📸 2" in collapsed
        assert show_label in collapsed
        assert "overview.jpg" not in collapsed
        assert "inverter.png" not in collapsed
        assert "show_photos=1" in collapsed
        assert "date=2026-10-09" in collapsed
        assert reverse("customer_portal:site_photo", args=[site_a.pk, "overview.jpg"]) not in collapsed
        mock_client.get_file.assert_not_called()
        response = client.get(url, {"show_photos": "1", "date": "2026-10-09"}, HTTP_ACCEPT_LANGUAGE=language)
        hidden_again = client.get(url, {"date": "2026-10-09"}).content.decode("utf-8")
        assert show_label in hidden_again
        assert "overview.jpg" not in hidden_again

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert hide_label in content
    assert "📸 2" in content
    assert "overview.jpg" in content
    assert "inverter.png" in content
    # Наличие Lightbox диалога и data-атрибутов
    assert "data-media-dialog" in content
    assert "data-media-preview" in content
    # Убедиться, что прямые URL Nextcloud не утекли в HTML
    assert "remote.php/dav" not in content


@patch("features.integrations.nextcloud.services.NextcloudWebDAVClient")
def test_customer_site_detail_shows_unavailable_state(mock_client_cls, portal_setup, client):
    """При ошибке облака экран объекта выводит явное предупреждение о недоступности."""
    alice = portal_setup["alice"]
    site_a = portal_setup["site_a"]

    mock_client = mock_client_cls.return_value
    mock_client.list_folder.side_effect = NextcloudWebDAVError("Cloud unreachable")

    client.force_login(alice)
    response = client.get(reverse("customer_portal:site", kwargs={"site_id": site_a.pk}))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Хранилище фотографий временно недоступно" in content
    # Не должно вводить в заблуждение, что фото отсутствуют
    assert "Нет фотографий" not in content


def test_customer_objects_renders_cached_badges(portal_setup, client):
    """Список объектов показывает бейдж из кеша без выполнения сетевых запросов."""
    alice = portal_setup["alice"]
    site_a = portal_setup["site_a"]

    # Кладём в кеш сводку для site_a по path-aware ключу
    cache.set(
        get_site_photo_cache_key(site_a),
        {"status": "ok", "is_available": True, "has_photos": True, "count": 7},
        timeout=900,
    )

    client.force_login(alice)
    response = client.get(reverse("customer_portal:objects"))
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "📸 7" in content
    assert "фотограф" in content.lower()


def test_cache_key_path_aware_and_rename_causes_fresh_listing_and_no_old_path(portal_setup):
    """Переименование группы или объекта меняет ключ кеша, вызывает свежий листинг и не тянет старый путь."""
    site = portal_setup["site_a"]
    group = portal_setup["group_a"]
    cache.clear()

    key1 = get_site_photo_cache_key(site)
    assert len(key1) < 200
    assert not any(character.isspace() for character in key1)
    assert str(site.pk) in key1

    mock_client = MagicMock()
    mock_client.list_folder.return_value = [
        {"name": "roof.jpg", "is_directory": False},
    ]
    mock_client.get_file.return_value = (VALID_JPEG, "image/jpeg")

    # 1. Первый запрос заполняет кеш для исходного пути
    s1 = get_site_photo_summary(site, client=mock_client)
    assert s1["count"] == 1
    initial_folder = "DLC Montage/AC/Anlage Alpha/2026-101 - Haus Alpha 1/Fotos"
    mock_client.list_folder.assert_called_once_with(initial_folder)

    # 2. Переименование группы
    group.name = "Anlage Alpha Umbenannt"
    group.save()
    site.refresh_from_db()
    site.group.refresh_from_db()

    key2 = get_site_photo_cache_key(site)
    assert key2 != key1
    assert not any(character.isspace() for character in key2)

    # 3. Запрос сводки после переименования не берет старый кеш, а выполняет свежий листинг
    mock_client.list_folder.reset_mock()
    s2 = get_site_photo_summary(site, client=mock_client)
    assert s2["count"] == 1
    new_folder = "DLC Montage/AC/Anlage Alpha Umbenannt/2026-101 - Haus Alpha 1/Fotos"
    mock_client.list_folder.assert_called_once_with(new_folder)

    # 4. Проксирование фото вычисляет актуальный канонический путь, а не старый путь из кеша
    mock_client.get_file.reset_mock()
    fetch_site_photo(site, "roof.jpg", client=mock_client)
    mock_client.get_file.assert_called_once_with(f"{new_folder}/roof.jpg")


def test_cached_badges_obtain_by_authorized_site_object(portal_setup):
    """Кешированный бейдж получается по объекту сайта, а не по голому int pk."""
    site = portal_setup["site_a"]
    cache.clear()

    cache.set(
        get_site_photo_cache_key(site),
        {"status": "ok", "is_available": True, "has_photos": True, "count": 5},
        timeout=900,
    )

    badge = get_cached_photo_summary(site)
    assert badge is not None
    assert badge["count"] == 5


def test_customer_site_detail_selector_has_no_photo_io(portal_setup):
    """Селектор customer_site_detail очищен от сетевого вызова фотофиксации и поля photo_summary."""
    site = portal_setup["site_a"]

    with patch("features.integrations.nextcloud.client.requests.request") as mock_req, patch(
        "features.integrations.nextcloud.client.requests.get"
    ) as mock_get:
        detail = customer_site_detail(site)
        mock_req.assert_not_called()
        mock_get.assert_not_called()

    assert not hasattr(detail, "photo_summary")


def test_excel_exports_forbid_webdav(portal_setup, client):
    """Выгрузки XLSX (Standort и Anlage) категорически не выполняют вызовы WebDAV/Nextcloud."""
    site = portal_setup["site_a"]
    group = portal_setup["group_a"]
    alice = portal_setup["alice"]

    with patch("features.integrations.nextcloud.client.requests.request") as mock_req, patch(
        "features.integrations.nextcloud.client.requests.get"
    ) as mock_get:
        # Прямой вызов функций генерации книг
        wb_site = site_workbook(site)
        assert len(wb_site) > 0
        wb_group = group_workbook(group)
        assert len(wb_group) > 0

        mock_req.assert_not_called()
        mock_get.assert_not_called()

        # Вызов через HTTP-представления
        client.force_login(alice)
        resp_site = client.get(reverse("customer_portal:accepted_work_xlsx", kwargs={"site_id": site.pk}))
        assert resp_site.status_code == 200
        resp_group = client.get(reverse("customer_portal:group_work_xlsx", kwargs={"group_id": group.pk}))
        assert resp_group.status_code == 200

        mock_req.assert_not_called()
        mock_get.assert_not_called()
