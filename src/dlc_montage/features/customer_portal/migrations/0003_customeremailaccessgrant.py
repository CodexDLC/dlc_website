"""Customer-owned, hashed and replaceable email access grants."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customer_portal", "0002_sitereview_item_decisions_sitereview_work_snapshot"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerEmailAccessGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("membership_updated_at", models.DateTimeField()),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                ("work_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="projects.client")),
                (
                    "issued_by",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
                ),
                (
                    "membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_access_grants",
                        to="customer_portal.clientmembership",
                    ),
                ),
            ],
        ),
    ]
