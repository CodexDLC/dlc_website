import core.private_storage
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import features.mbg_reports.models


class Migration(migrations.Migration):
    dependencies = [
        ("mbg_reports", "0003_mbgdailyreport_workforce"),
        ("projects", "0005_acobject_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PerformanceExport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fingerprint", models.CharField(max_length=64, unique=True)),
                ("template_version", models.CharField(default="prototype-1", max_length=20)),
                ("snapshot", models.JSONField()),
                (
                    "file",
                    models.FileField(
                        storage=core.private_storage.private_storage,
                        upload_to=features.mbg_reports.models.performance_export_path,
                    ),
                ),
                ("filename", models.CharField(max_length=250)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="performance_exports",
                        to="projects.acobject",
                    ),
                ),
            ],
            options={"ordering": ["-pk"]},
        )
    ]
