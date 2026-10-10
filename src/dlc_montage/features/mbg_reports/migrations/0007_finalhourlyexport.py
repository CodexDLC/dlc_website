import core.private_storage
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import features.mbg_reports.models


class Migration(migrations.Migration):
    dependencies = [
        ("mbg_reports", "0006_alter_performanceexport_group"),
        ("projects", "0007_alter_projectgroup_client_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FinalHourlyExport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("fingerprint", models.CharField(max_length=64, unique=True)),
                ("template_version", models.CharField(default="ac-final-hours-1", max_length=24)),
                ("snapshot", models.JSONField()),
                (
                    "file",
                    models.FileField(
                        storage=core.private_storage.private_storage,
                        upload_to=features.mbg_reports.models.final_hourly_export_path,
                    ),
                ),
                ("filename", models.CharField(max_length=250)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="final_hourly_exports",
                        to="projects.projectgroup",
                    ),
                ),
            ],
            options={"ordering": ["-pk"]},
        )
    ]
