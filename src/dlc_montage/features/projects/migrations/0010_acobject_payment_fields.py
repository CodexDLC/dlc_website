"""Добавить поля оплаты (is_paid, paid_at, paid_by, payment_note) к Standort (AcObject)."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0009_siteworkitem_readiness"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="acobject",
            name="is_paid",
            field=models.BooleanField(default=False, verbose_name="Zahlungsstatus Bezahlt"),
        ),
        migrations.AddField(
            model_name="acobject",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Bezahlt am"),
        ),
        migrations.AddField(
            model_name="acobject",
            name="paid_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="paid_ac_objects",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Bezahlt von",
            ),
        ),
        migrations.AddField(
            model_name="acobject",
            name="payment_note",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Zahlungsnotiz"),
        ),
    ]
