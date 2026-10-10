"""Добавить маршрут от UV-PV к новой HPAS."""

from django.db import migrations


def seed_uv_hpas_route(apps, schema_editor):
    CableRoute = apps.get_model("work_catalog", "CableRoute")
    CableRoute.objects.using(schema_editor.connection.alias).update_or_create(
        code="uv-hpas-new",
        defaults={
            "name_de": "UV-PV → neue HPAS",
            "name_ru": "UV-PV → новая HPAS",
            "is_active": True,
            "sort_order": 4,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("work_catalog", "0010_seed_photo_documentation")]
    operations = [migrations.RunPython(seed_uv_hpas_route, migrations.RunPython.noop)]
