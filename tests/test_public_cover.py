"""The anonymous public cover has localized copy and a working cabinet entry."""

import pytest


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
