"""Рабочие страницы, независимые итоги и закрытые вложения."""

from datetime import time
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from features.internal_time.services import review_report, save_report
from features.management_reports.selectors import monthly_summary
from features.project_media.models import ProjectFile
from features.project_media.services import set_publicity, upload_file
from features.projects.models import AcObject, ProjectGroup
from features.staff.models import Employee
from features.staff.services import save_employee
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(ProjectFile._meta.get_field("file"), "storage", FileSystemStorage(location=tmp_path))
    admin = get_user_model().objects.create_user(username="admin", is_superuser=True)
    worker = get_user_model().objects.create_user(username="worker")
    employee = Employee.objects.create(
        first_name="Test",
        last_name="Employee",
        user=worker,
        is_foreman=True,
        has_ac_access=True,
        hourly_rate_eur=Decimal("13.90"),
    )
    group = ProjectGroup.objects.create(name="Anlage", responsible=worker)
    return admin, worker, employee, group


def picture():
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buffer, format="PNG")
    return SimpleUploadedFile("final.png", buffer.getvalue(), content_type="image/png")


def pdf_document():
    return SimpleUploadedFile("plan.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")


def test_month_separates_pending_and_accepted(data, client):
    admin, worker, employee, group = data
    today = timezone.localdate()
    report = save_report(
        actor=admin,
        data=dict(
            project_group=group,
            direction="ac",
            work_date=today,
            starts_at=time(7),
            ends_at=time(18),
            lunch_minutes=30,
            note="",
            work_description="",
            submission_key=uuid4(),
        ),
        participants=[dict(employee=employee, deduction_minutes=60)],
        submit=True,
    )
    summary = monthly_summary(today.year, today.month)
    assert summary["people"][0]["submitted"] == 600
    assert summary["people"][0]["accepted"] == 0
    review_report(actor=admin, report_id=report.pk, version=report.version, decision="accept")
    assert monthly_summary(today.year, today.month)["people"][0]["accepted"] == 600
    assert monthly_summary(today.year, today.month)["people"][0]["accepted_gross"] == Decimal("139.00")
    client.force_login(admin)
    assert client.get(reverse("monthly_hours")).status_code == 200
    response = client.get(reverse("monthly_hours"), {"month": today.strftime("%Y-%m"), "export": "xlsx"})
    assert response.status_code == 200
    from openpyxl import load_workbook

    book = load_workbook(BytesIO(response.content))
    assert book["Stunden"]["B2"].value == 10
    assert book["Stunden"]["D2"].value == 13.9
    assert book["Stunden"]["E2"].value == "=B2*D2"
    client.force_login(worker)
    assert client.get(reverse("monthly_hours")).status_code == 403


@pytest.mark.django_db(transaction=True)
def test_private_files_and_publicity(data, client):
    admin, worker, _employee, group = data
    item = upload_file(actor=worker, group_id=group.pk, upload=picture(), kind="photo")
    assert not item.is_public
    assert item.file.name.startswith(f"projects/{group.pk}/general/photo/")
    with pytest.raises(PermissionDenied):
        set_publicity(actor=worker, file_id=item.pk, public=True)
    set_publicity(actor=admin, file_id=item.pk, public=True)
    client.force_login(worker)
    assert client.get(reverse("project_media:list", args=[group.pk])).status_code == 200
    response = client.get(reverse("project_media:download", args=[item.pk]))
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    response.close()
    outsider = get_user_model().objects.create_user(username="outsider")
    client.force_login(outsider)
    assert client.get(reverse("project_media:download", args=[item.pk])).status_code == 403
    client.logout()
    assert client.get(reverse("project_media:download", args=[item.pk])).status_code == 302


def test_private_image_preview_is_inline_and_protected(data, client):
    _admin, worker, _employee, group = data
    item = upload_file(actor=worker, group_id=group.pk, upload=picture(), kind="photo", caption="Final view")
    client.force_login(worker)

    response = client.get(reverse("project_media:preview", args=[item.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["Content-Disposition"].startswith("inline;")
    assert response["Cache-Control"] == "private, no-store"
    assert response["X-Content-Type-Options"] == "nosniff"
    outsider = get_user_model().objects.create_user(username="preview-outsider")
    client.force_login(outsider)
    assert client.get(reverse("project_media:preview", args=[item.pk])).status_code == 403
    response.close()


def test_private_pdf_preview_can_be_embedded_only_on_same_origin(data, client):
    _admin, worker, _employee, group = data
    item = upload_file(actor=worker, group_id=group.pk, upload=pdf_document(), kind="document")
    client.force_login(worker)

    response = client.get(reverse("project_media:preview", args=[item.pk]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith("inline;")
    assert response["X-Frame-Options"] == "SAMEORIGIN"
    response.close()


def test_media_gallery_and_filters(data, client):
    _admin, worker, _employee, group = data
    site = AcObject.objects.create(group=group, name="Haus 42")
    photo = upload_file(
        actor=worker,
        group_id=group.pk,
        upload=picture(),
        kind="photo",
        site=site,
        caption="Final AC photo",
    )
    upload_file(
        actor=worker,
        group_id=group.pk,
        upload=pdf_document(),
        kind="plan",
        caption="Electrical plan",
    )
    client.force_login(worker)

    response = client.get(reverse("project_media:list", args=[group.pk]))
    content = response.content.decode()
    assert "project-media-grid" in content
    assert "data-media-preview" in content
    assert reverse("project_media:preview", args=[photo.pk]) in content
    assert reverse("project_media:download", args=[photo.pk]) in content
    assert "Final AC photo" in content
    assert "Electrical plan" in content

    photo_response = client.get(reverse("project_media:list", args=[group.pk]), {"kind": "photo"})
    assert "Final AC photo" in photo_response.content.decode()
    assert "Electrical plan" not in photo_response.content.decode()

    general_response = client.get(reverse("project_media:list", args=[group.pk]), {"site": "general"})
    assert "Final AC photo" not in general_response.content.decode()
    assert "Electrical plan" in general_response.content.decode()

    site_response = client.get(reverse("project_media:list", args=[group.pk]), {"site": site.pk})
    assert "Final AC photo" in site_response.content.decode()
    assert "Electrical plan" not in site_response.content.decode()


def test_upload_rejects_wrong_site_and_fake_images(data):
    admin, _worker, _employee, group = data
    other = ProjectGroup.objects.create(name="Other")
    site = AcObject.objects.create(group=other, name="House")
    with pytest.raises(ValidationError):
        upload_file(actor=admin, group_id=group.pk, upload=picture(), kind="photo", site=site)
    with pytest.raises(ValidationError):
        upload_file(
            actor=admin, group_id=group.pk, upload=SimpleUploadedFile("fake.png", b"not an image"), kind="photo"
        )
    with pytest.raises(ValidationError):
        upload_file(
            actor=admin,
            group_id=group.pk,
            upload=SimpleUploadedFile("attack.html", b"<script>alert(1)</script>"),
            kind="document",
        )
    assert ProjectFile.objects.count() == 0


def test_staff_management_is_admin_only(data, client):
    admin, worker, employee, _group = data
    with pytest.raises(PermissionDenied):
        save_employee(actor=worker, data={"first_name": "New"})
    client.force_login(admin)
    assert client.get(reverse("staff_employee_new")).status_code == 200
    response = client.post(
        reverse("staff_employee_edit", args=[employee.pk]),
        {
            "first_name": "Edited",
            "last_name": "Employee",
            "employment_status": "active",
            "hourly_rate_eur": "15.50",
            "is_foreman": "on",
            "has_ac_access": "on",
            "user": worker.pk,
        },
    )
    assert response.status_code == 302
    employee.refresh_from_db()
    assert employee.first_name == "Edited"
    assert employee.hourly_rate_eur == Decimal("15.50")
    client.force_login(worker)
    assert client.get(reverse("staff_employee_new")).status_code == 403
