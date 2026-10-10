"""Сохранять решения менеджера по позициям плана Standort."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0008_siteworkitem"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="siteworkitem", name="is_required", field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="siteworkitem", name="completion_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="siteworkitem", name="completion_confirmed_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="confirmed_site_work_items", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="siteworkitem", name="not_required_reason", field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="siteworkitem", name="not_required_at", field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="siteworkitem", name="not_required_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="excluded_site_work_items", to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
