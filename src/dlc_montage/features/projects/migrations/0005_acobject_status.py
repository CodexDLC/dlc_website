from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0004_acobject_remove_project_client_and_more")]

    operations = [
        migrations.AddField(
            model_name="acobject",
            name="status",
            field=models.CharField(
                choices=[
                    ("not_started", "Не начато"),
                    ("started", "Начато"),
                    ("completed", "Завершено"),
                ],
                default="not_started",
                max_length=16,
                verbose_name="Готовность Standort",
            ),
        )
    ]
