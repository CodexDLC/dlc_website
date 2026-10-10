"""Локальный стенд UI с отдельной временной базой и тестовыми сотрудниками."""

import os
import sys
import tempfile
from pathlib import Path
from secrets import token_urlsafe

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "src" / "dlc_montage")]
os.environ["DJANGO_SETTINGS_MODULE"] = "dlc_montage.core.settings.test"


def main():
    """Поднять стенд на loopback; временная база удаляется при остановке."""
    from django.conf import settings

    with tempfile.TemporaryDirectory(prefix="dlc-report-preview-") as temporary:
        settings.DATABASES["default"]["NAME"] = str(Path(temporary) / "preview.sqlite3")
        settings.SESSION_ENGINE = "django.contrib.sessions.backends.db"
        settings.PRIVATE_MEDIA_ROOT = Path(temporary) / "private"
        settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
        import django

        django.setup()
        from django.core.management import call_command

        call_command("migrate", verbosity=0)
        from django.contrib.auth import get_user_model
        from features.crews.services import save_team
        from features.projects.models import AcObject, ProjectGroup
        from features.staff.models import Employee

        password = token_urlsafe(18)
        admin = get_user_model().objects.create_user(
            username="preview", password=password, is_staff=True, is_superuser=True
        )
        worker = Employee.objects.create(first_name="Тестовый", last_name="Бригадир", user=admin, is_foreman=True)
        second = Employee.objects.create(first_name="Второй", last_name="Участник")
        group = ProjectGroup.objects.create(name="Тест · Berlin 38, 40, 42", responsible=admin)
        AcObject.objects.create(group=group, name="Haus 42", address="Berlin, Teststraße 42", project_number="TEST-42")
        save_team(actor=admin, name="Тестовая команда", owner=worker, members=[worker, second])
        print(f"PREVIEW LOGIN: preview / {password}", flush=True)
        from django.db import connections

        try:
            call_command("runserver", "127.0.0.1:8001", use_reloader=False)
        finally:
            connections.close_all()


if __name__ == "__main__":
    main()
