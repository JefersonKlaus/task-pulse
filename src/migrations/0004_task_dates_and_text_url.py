"""Tasks lose ``date``; start/finish dates take over. Project URL is plain text.

* ``started_on`` becomes required (default: the creation date). Existing
  tasks without a start date get their old ``date`` value, so no date is
  lost before ``date`` is removed.
* ``time_spent`` defaults to 0; ordering is by ``started_on``.
* ``Project.url`` becomes a plain text field so any git URL can be stored.

Not reversible: the removed ``date`` column cannot be rebuilt.
"""

import django.core.validators
import django.utils.timezone
from django.db import migrations, models


def copy_date_to_missing_started_on(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    Task.objects.filter(started_on__isnull=True).update(started_on=models.F("date"))


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0003_project_url_and_task_details"),
    ]

    operations = [
        migrations.RunPython(copy_date_to_missing_started_on),
        migrations.AlterField(
            model_name="task",
            name="started_on",
            field=models.DateField(
                default=django.utils.timezone.localdate,
                help_text="Data de criação da tarefa; pode ser corrigida.",
            ),
        ),
        migrations.RemoveField(
            model_name="task",
            name="date",
        ),
        migrations.AlterField(
            model_name="task",
            name="finished_on",
            field=models.DateField(
                blank=True,
                help_text=(
                    "Preenchida ao mudar o status para Review ou Done; "
                    "pode ser corrigida."
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="time_spent",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Tempo gasto em horas.",
                max_digits=6,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterModelOptions(
            name="task",
            options={
                "ordering": ["-started_on", "name"],
                "verbose_name": "tarefa",
                "verbose_name_plural": "tarefas",
            },
        ),
        migrations.AlterField(
            model_name="project",
            name="url",
            field=models.CharField(max_length=255, verbose_name="URL"),
        ),
    ]
