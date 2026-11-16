from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .domain.git_urls import is_web_url, project_name_from_url
from .domain.task_lifecycle import resolve_finished_on
from .domain.task_status import TaskStatus


class Project(models.Model):
    # Plain text so any git URL (https or SSH) can be stored.
    url = models.CharField("URL", max_length=255)
    # blank=True: when left empty, save() fills it in from the URL.
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "projeto"
        verbose_name_plural = "projetos"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.name.strip():
            self.name = project_name_from_url(self.url)
        super().save(*args, **kwargs)

    @property
    def web_url(self):
        """The URL if it is safe to use as a link (http/https), else ""."""
        return self.url if is_web_url(self.url) else ""


class TaskQuerySet(models.QuerySet):
    def started_between(self, start, end):
        """Tasks whose start date is in ``[start, end]``."""
        return self.filter(started_on__range=(start, end))

    def with_statuses(self, statuses):
        return self.filter(status__in=statuses)


class Task(models.Model):
    Status = TaskStatus  # Task.Status.DONE, as usual in Django

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    name = models.CharField(max_length=255)
    # Identifier of the task in an external system (set by file imports).
    external_id = models.CharField(
        "ID externo",
        max_length=100,
        blank=True,
        help_text="Identificador da tarefa no sistema de origem.",
    )
    description = models.TextField(
        blank=True,
        help_text="Objetivos da tarefa.",
    )
    acceptance_criteria = models.TextField(
        blank=True,
        help_text="Como julgar que a tarefa está concluída (como testá-la).",
    )
    # Whole minutes, so repeated additions stay exact (see domain.durations).
    # The explicit validator keeps full_clean() strict on every Django version
    # (4.2 on SQLite does not add one for PositiveIntegerField).
    minutes_spent = models.PositiveIntegerField(
        default=0,
        help_text="Tempo gasto, em minutos.",
        validators=[MinValueValidator(0)],
    )
    started_on = models.DateField(
        default=timezone.localdate,
        help_text="Data de criação da tarefa; pode ser corrigida.",
    )
    finished_on = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Preenchida ao mudar o status para Review ou Done; pode ser corrigida."
        ),
    )
    status = models.CharField(
        max_length=8,
        choices=TaskStatus.choices,
        default=TaskStatus.DOING,
    )

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ["-started_on", "name"]
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"
        constraints = [
            # An external id identifies one task per project; blank is allowed
            # for any number of tasks.
            models.UniqueConstraint(
                fields=["project", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_task_external_id_per_project",
                violation_error_message=(
                    "Já existe uma tarefa com este ID externo neste projeto."
                ),
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.started_on and self.finished_on and self.finished_on < self.started_on:
            raise ValidationError(
                {"finished_on": "A data de término não pode ser anterior ao início."}
            )

    def add_time(self, minutes):
        """Add ``minutes`` to the time spent.

        The sum is done by the database, so two additions made at the same
        time are both kept.
        """
        Task.objects.filter(pk=self.pk).update(
            minutes_spent=models.F("minutes_spent") + minutes
        )
        self.refresh_from_db(fields=["minutes_spent"])

    def save(self, *args, **kwargs):
        previous_status, previous_finished_on = self._stored_status_and_finish()
        self.finished_on = resolve_finished_on(
            status=self.status,
            finished_on=self.finished_on,
            previous_status=previous_status,
            previous_finished_on=previous_finished_on,
            today=timezone.localdate(),
        )
        super().save(*args, **kwargs)

    def _stored_status_and_finish(self):
        """``(status, finished_on)`` as in the database; ``(None, None)`` if new."""
        if self._state.adding:
            return None, None
        stored = (
            Task.objects.filter(pk=self.pk).values_list("status", "finished_on").first()
        )
        return stored or (None, None)
