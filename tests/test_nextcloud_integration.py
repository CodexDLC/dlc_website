"""Тесты интеграции с Nextcloud MBG по WebDAV и автосоздания папок."""

from unittest.mock import MagicMock, patch
import pytest
import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache

from features.integrations.nextcloud.client import NextcloudWebDAVClient, NextcloudWebDAVError
from features.integrations.nextcloud.services import (
    ensure_group_folders,
    ensure_site_folders,
    get_group_folder_path,
    get_site_folder_name,
    get_site_folder_path,
    get_site_photo_summary,
)
from features.projects.models import AcObject, ProjectGroup
from features.projects.services import save_group, save_object

User = get_user_model()


@pytest.fixture
def manager_user(db):
    return User.objects.create_user(
        username="test_manager",
        email="manager@dlc.de",
        password="secretpassword",
        is_superuser=True,
    )


@pytest.fixture
def project_group(db, manager_user):
    return ProjectGroup.objects.create(
        name="Huttwiler Weg 1-10",
        responsible=manager_user,
        has_ac=True,
    )


@pytest.fixture
def ac_site(db, project_group):
    return AcObject.objects.create(
        group=project_group,
        name="Huttwiler Weg 5",
        address="Huttwiler Weg 5",
        project_number="2026-1505",
    )


def test_path_formatting(project_group, ac_site):
    """Проверка генерации путей к папкам Nextcloud."""
    assert get_group_folder_path(project_group) == "DLC Montage/AC/Huttwiler Weg 1-10"
    assert get_site_folder_name(ac_site) == "2026-1505 - Huttwiler Weg 5"
    assert (
        get_site_folder_path(ac_site)
        == "DLC Montage/AC/Huttwiler Weg 1-10/2026-1505 - Huttwiler Weg 5"
    )


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_ensure_folder_mkcol_success(mock_request):
    """MKCOL возвращает 201 (создано) или 405 (уже существует)."""
    resp_201 = MagicMock()
    resp_201.status_code = 201
    resp_405 = MagicMock()
    resp_405.status_code = 405
    mock_request.side_effect = [resp_201, resp_405]

    client = NextcloudWebDAVClient(base_url="https://cloud.test/remote.php/dav/files/DLC/")
    result = client.ensure_folder("DLC Montage/AC")

    assert result is True
    assert mock_request.call_count == 2


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_ensure_folder_network_error(mock_request):
    """Сетевая ошибка выбрасывает NextcloudWebDAVError."""
    mock_request.side_effect = requests.RequestException("Timeout")

    client = NextcloudWebDAVClient(base_url="https://cloud.test/remote.php/dav/files/DLC/")
    with pytest.raises(NextcloudWebDAVError):
        client.ensure_folder("DLC Montage/AC")


@patch("features.integrations.nextcloud.client.requests.request")
def test_client_list_folder_xml_parsing(mock_request):
    """Парсинг ответа PROPFIND 207 Multi-Status."""
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
<d:multistatus xmlns:d="DAV:">
    <d:response>
        <d:href>/remote.php/dav/files/DLC/Fotos/</d:href>
        <d:propstat>
            <d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop>
            <d:status>HTTP/1.1 200 OK</d:status>
        </d:propstat>
    </d:response>
    <d:response>
        <d:href>/remote.php/dav/files/DLC/Fotos/photo1.jpg</d:href>
        <d:propstat>
            <d:prop><d:resourcetype/></d:prop>
            <d:status>HTTP/1.1 200 OK</d:status>
        </d:propstat>
    </d:response>
</d:multistatus>"""
    resp = MagicMock()
    resp.status_code = 207
    resp.text = xml_data
    mock_request.return_value = resp

    client = NextcloudWebDAVClient(
        base_url="https://cloud.test/remote.php/dav/files/DLC/",
        username="DLC",
    )
    items = client.list_folder("Fotos")

    assert len(items) == 1
    assert items[0]["name"] == "photo1.jpg"
    assert items[0]["is_directory"] is False


def test_ensure_site_folders_service(ac_site):
    """Сервис ensure_site_folders создаёт Dokumente и Fotos."""
    mock_client = MagicMock()
    mock_client.ensure_folder.return_value = True

    ok = ensure_site_folders(ac_site, client=mock_client)
    assert ok is True

    site_path = "DLC Montage/AC/Huttwiler Weg 1-10/2026-1505 - Huttwiler Weg 5"
    mock_client.ensure_folder.assert_any_call(f"{site_path}/Dokumente")
    mock_client.ensure_folder.assert_any_call(f"{site_path}/Fotos")


def test_get_site_photo_summary(ac_site):
    """Проверка сбора сводки фотографий с кешированием."""
    cache.clear()
    mock_client = MagicMock()
    mock_client.list_folder.return_value = [
        {"name": "overview.jpg", "is_directory": False},
        {"name": "details.PNG", "is_directory": False},
        {"name": "protocol.pdf", "is_directory": False},
        {"name": "subfolder", "is_directory": True},
    ]

    summary = get_site_photo_summary(ac_site, client=mock_client)

    assert summary["has_photos"] is True
    assert summary["count"] == 2
    assert len(summary["photos"]) == 2

    # Повторный вызов берёт из кеша, не трогая клиент
    cached_summary = get_site_photo_summary(ac_site, client=None)
    assert cached_summary["count"] == 2


@pytest.mark.django_db(transaction=True)
@patch("features.projects.services.ensure_group_folders")
def test_save_group_triggers_nextcloud(mock_ensure_group, manager_user):
    """save_group вызывает создание папок в Nextcloud после коммита."""
    data = {"name": "Neues Projekt 2026", "has_ac": True}
    group = save_group(actor=manager_user, data=data)
    assert group.name == "Neues Projekt 2026"
    mock_ensure_group.assert_called_once_with(group)


@pytest.mark.django_db(transaction=True)
@patch("features.projects.group_services.ensure_group_folders")
def test_create_project_group_triggers_nextcloud(mock_ensure_group, manager_user):
    """create_project_group вызывает создание папок в Nextcloud после коммита."""
    from features.projects.group_services import create_project_group

    group = create_project_group(actor=manager_user, name="Quick Project 2026")
    assert group.name == "Quick Project 2026"
    mock_ensure_group.assert_called_once_with(group)


@pytest.mark.django_db(transaction=True)
@patch("features.projects.services.ensure_site_folders")
def test_save_object_triggers_nextcloud(mock_ensure_site, manager_user, project_group):
    """save_object вызывает создание папок в Nextcloud после коммита."""
    data = {
        "name": "Haus 1",
        "address": "Sonnenallee 1",
        "project_number": "2026-5555",
        "status": "not_started",
        "is_active": True,
    }
    site = save_object(actor=manager_user, group=project_group, data=data)
    assert site.project_number == "2026-5555"
    mock_ensure_site.assert_called_once_with(site)


@patch("features.integrations.nextcloud.client.requests.request")
def test_network_failure_does_not_break_db_save(mock_request, manager_user, project_group):
    """Сбой связи с Nextcloud логируется, но не прерывает сохранение в БД."""
    mock_request.side_effect = requests.RequestException("Connection refused")

    data = {
        "name": "Haus 2",
        "address": "Sonnenallee 2",
        "project_number": "2026-5556",
        "status": "not_started",
        "is_active": True,
    }
    # Должно выполниться успешно без выброса исключения в пользователя
    site = save_object(actor=manager_user, group=project_group, data=data)
    assert site.pk is not None
    assert AcObject.objects.filter(pk=site.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_editing_existing_records_does_not_recreate_nextcloud_folders(manager_user, project_group, ac_site):
    with patch("features.projects.services.ensure_group_folders") as group_create, patch(
        "features.projects.services.ensure_site_folders"
    ) as site_create:
        save_group(actor=manager_user, group_id=project_group.pk, data={"has_dc": True})
        save_object(actor=manager_user, group=project_group, object_id=ac_site.pk,
                    data={"project_number": "2026-1039"})
    group_create.assert_not_called()
    site_create.assert_not_called()
