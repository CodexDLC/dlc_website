import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mbg_reports", "0009_mbgworkentry_custom_description"),
        ("projects", "0008_siteworkitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="mbgworkentry",
            name="work_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="mbg_entries",
                to="projects.siteworkitem",
            ),
        ),
        migrations.AddField(
            model_name="mbgworkentry",
            name="completed_quantity",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddConstraint(
            model_name="mbgworkentry",
            constraint=models.CheckConstraint(
                condition=models.Q(completed_quantity__gte=0) | models.Q(completed_quantity__isnull=True),
                name="mbg_entry_nonnegative_completed_quantity",
            ),
        ),
        migrations.AddConstraint(
            model_name="mbgworkentry",
            constraint=models.CheckConstraint(
                condition=(models.Q(work_item__isnull=True) & models.Q(completed_quantity__isnull=True))
                | (models.Q(work_item__isnull=False) & models.Q(completed_quantity__isnull=False)),
                name="mbg_entry_work_item_delta_together",
            ),
        ),
    ]
