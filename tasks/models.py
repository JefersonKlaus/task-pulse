from django.db import models
from django.core.validators import MinValueValidator


class Repository(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "repositório"
        verbose_name_plural = "repositórios"

    def __str__(self):
        return self.name


class Project(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "projeto"
        verbose_name_plural = "projetos"

    def __str__(self):
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        REJECTED = "REJECTED", "Rejeitado"
        DONE = "DONE", "Done"
        REVIEW = "REVIEW", "Review"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    external_id = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    time_spent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Tempo gasto em horas.",
        validators=[MinValueValidator(0)],
    )
    nickname = models.CharField(max_length=255)
    language = models.CharField(max_length=100)
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.REVIEW,
    )

    class Meta:
        ordering = ["-date", "nickname"]
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"

    def __str__(self):
        return self.nickname
