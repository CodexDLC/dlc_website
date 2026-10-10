"""The anonymous public cover has localized copy and a working cabinet entry."""

import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_cover_text_can_be_changed_in_content_file_and_stays_escaped(client, monkeypatch):
    from features.main.content import PUBLIC_COPY

    monkeypatch.setitem(PUBLIC_COPY["ru"], "hero_title", "Новый текст <strong>обложки</strong>")
    russian = client.get("/ru/").content.decode()
    german = client.get("/de/").content.decode()
    assert "Новый текст &lt;strong&gt;обложки&lt;/strong&gt;" in russian
    assert "Новый текст" not in german
    assert "Gemeinsam Solarprojekte umsetzen." in german


@pytest.mark.django_db
@override_settings(DEBUG=False)
@pytest.mark.parametrize("language", ["ru", "de"])
def test_public_error_page_keeps_shared_navigation(client, language):
    response = client.get(f"/{language}/missing-public-page/")
    assert response.status_code == 404
    assert f'href="/{language}/cabinet/login/"' in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "heading", "empty_contact"),
    [
        ("ru", "Реализуем солнечные проекты вместе.", "Контактные данные будут добавлены."),
        ("de", "Gemeinsam Solarprojekte umsetzen.", "Die Kontaktdaten werden ergänzt."),
    ],
)
def test_public_cover_is_localized_and_has_no_empty_contact_actions(client, language, heading, empty_contact):
    response = client.get(f"/{language}/")
    assert response.status_code == 200
    html = response.content.decode()
    assert f'<html lang="{language}">' in html
    assert heading in html
    assert empty_contact in html
    assert f'href="/{language}/cabinet/login/"' in html
    assert 'value="ru"' in html and 'value="de"' in html
    assert 'href="mailto:"' not in html
    assert 'href="tel:"' not in html
    assert "The public website is being prepared." not in html
