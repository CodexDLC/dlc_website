from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0007_alter_projectgroup_client_and_more"),
        ("work_catalog", "0012_update_piecework_35_eur_rates"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteWorkItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=255)),
                ("planned_quantity", models.DecimalField(decimal_places=2, max_digits=8)),
                ("unit_snapshot", models.CharField(max_length=32)),
                ("with_underconstruction", models.BooleanField(default=False)),
                (
                    "cable_type",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="work_catalog.cabletype"
                    ),
                ),
                (
                    "route",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="work_catalog.cableroute"
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="work_items", to="projects.acobject"
                    ),
                ),
                (
                    "work_type",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="work_catalog.worktype"),
                ),
            ],
            options={"ordering": ["site_id", "pk"]},
        ),
        migrations.AddConstraint(
            model_name="siteworkitem",
            constraint=models.CheckConstraint(
                condition=models.Q(planned_quantity__gt=Decimal("0")), name="site_work_item_positive_plan"
            ),
        ),
    ]
