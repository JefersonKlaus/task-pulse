"""Move URL/description from Repository onto Project and extend Task.

* Project gets ``url`` and ``description``, copied from its repository,
  and the Repository model is removed. Projects whose repository had no
  URL end up with an empty URL and must get one before their next edit.
* Task: ``nickname`` is renamed to ``name``; ``language`` and
  ``external_id`` are removed (their data is dropped); ``description``,
  ``acceptance_criteria``, ``started_on`` and ``finished_on`` are added;
  status gains DOING, which becomes the default.

Not reversible: the repository data and the removed task columns
cannot be rebuilt.
"""

from django.db import migrations, models


def copy_repository_data_to_projects(apps, schema_editor):
    Project = apps.get_model("tasks", "Project")
    for project in Project.objects.select_related("repository"):
        project.url = project.repository.url or ""
        project.description = project.repository.description
        project.save(update_fields=["url", "description"])


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0002_repository_url"),
    ]

    operations = [
        # Project: take over url/description from Repository.
        migrations.AddField(
            model_name="project",
            name="url",
            field=models.URLField(default="", max_length=255, verbose_name="URL"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="project",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(copy_repository_data_to_projects),
        migrations.RemoveField(
            model_name="project",
            name="repository",
        ),
        migrations.DeleteModel(
            name="Repository",
        ),
        migrations.AlterField(
            model_name="project",
            name="name",
            field=models.CharField(blank=True, max_length=255),
        ),
        # Task: new field set.
        migrations.RenameField(
            model_name="task",
            old_name="nickname",
            new_name="name",
        ),
        migrations.RemoveField(
            model_name="task",
            name="language",
        ),
        migrations.RemoveField(
            model_name="task",
            name="external_id",
        ),
        migrations.AddField(
            model_name="task",
            name="description",
            field=models.TextField(blank=True, help_text="Objetivos da tarefa."),
        ),
        migrations.AddField(
            model_name="task",
            name="acceptance_criteria",
            field=models.TextField(
                blank=True,
                help_text="Como julgar que a tarefa está concluída (como testá-la).",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="started_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="finished_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="status",
            field=models.CharField(
                choices=[
                    ("DOING", "Doing"),
                    ("REVIEW", "Review"),
                    ("DONE", "Done"),
                    ("REJECTED", "Rejeitado"),
                ],
                default="DOING",
                max_length=8,
            ),
        ),
        migrations.AlterModelOptions(
            name="task",
            options={
                "ordering": ["-date", "name"],
                "verbose_name": "tarefa",
                "verbose_name_plural": "tarefas",
            },
        ),
    ]
