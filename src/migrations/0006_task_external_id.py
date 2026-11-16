"""Tasks get an external id (from imported files), unique per project."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0005_task_minutes_spent"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="external_id",
            field=models.CharField(
                blank=True,
                help_text="Identificador da tarefa no sistema de origem.",
                max_length=100,
                verbose_name="ID externo",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.UniqueConstraint(
                condition=models.Q(("external_id", ""), _negated=True),
                fields=("project", "external_id"),
                name="unique_task_external_id_per_project",
                violation_error_message=(
                    "Já existe uma tarefa com este ID externo neste projeto."
                ),
            ),
        ),
    ]
