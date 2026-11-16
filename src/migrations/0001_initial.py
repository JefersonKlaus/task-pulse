from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Repository",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "repositório",
                "verbose_name_plural": "repositórios",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "repository",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="projects",
                        to="tasks.repository",
                    ),
                ),
            ],
            options={
                "verbose_name": "projeto",
                "verbose_name_plural": "projetos",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("external_id", models.CharField(blank=True, max_length=255)),
                ("date", models.DateField()),
                (
                    "time_spent",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Tempo gasto em horas.",
                        max_digits=6,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                ("nickname", models.CharField(max_length=255)),
                ("language", models.CharField(max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("REJECTED", "Rejeitado"),
                            ("DONE", "Done"),
                            ("REVIEW", "Review"),
                        ],
                        default="REVIEW",
                        max_length=8,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="tasks.project",
                    ),
                ),
            ],
            options={
                "verbose_name": "tarefa",
                "verbose_name_plural": "tarefas",
                "ordering": ["-date", "nickname"],
            },
        ),
    ]
