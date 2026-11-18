from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .domain.git_urls import is_web_url, project_name_from_url
from .domain.task_lifecycle import resolve_finished_on
from .domain.task_status import TaskStatus


class Provider(models.Model):
    """A company that gives the work (Alignerr, Etho, …): projects belong to
    one, and every report can be filtered by it."""

    name = models.CharField(_("nome"), max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("empresa")
        verbose_name_plural = _("empresas")
        constraints = [
            # "Etho" and "etho" are the same company.
            models.UniqueConstraint(
                Lower("name"),
                name="unique_provider_name",
                violation_error_message=_("Já existe uma empresa com este nome."),
            ),
        ]

    def __str__(self):
        return self.name


class ProjectQuerySet(models.QuerySet):
    def of_provider(self, provider):
        """The provider's projects; every project when ``provider`` is None."""
        return self if provider is None else self.filter(provider=provider)


class Project(models.Model):
    # Plain text so any git URL (https or SSH) can be stored.
    url = models.CharField("URL", max_length=255)
    # blank=True: when left empty, save() fills it in from the URL.
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional: projects created before companies existed have none.
    # Deleting a company leaves its projects without one.
    provider = models.ForeignKey(
        Provider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name=_("empresa"),
    )

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name = _("projeto")
        verbose_name_plural = _("projetos")

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


class PaymentQuerySet(models.QuerySet):
    """A payment's company is not stored: it is the company of all its tasks'
    projects (see ``Payment.provider_name``). So payments registered before
    their projects had a company get one as soon as the projects do.
    """

    def with_task_totals(self):
        """Adds ``task_count`` and ``minutes`` (time of its tasks) to each,
        and what ``provider_name`` needs."""
        tasks_provider = "tasks__project__provider"
        return self.annotate(
            task_count=models.Count("tasks"),
            minutes=Coalesce(models.Sum("tasks__minutes_spent"), 0),
            provider_count=models.Count(tasks_provider, distinct=True),
            tasks_without_provider=models.Count(
                "tasks", filter=models.Q(**{f"{tasks_provider}__isnull": True})
            ),
            any_provider_name=models.Max(f"{tasks_provider}__name"),
        )

    def of_provider(self, provider):
        """Payments whose tasks are all of ``provider`` (every payment when
        ``provider`` is None). A payment mixing companies is in none."""
        if provider is None:
            return self
        tasks = Task.objects.filter(payment=models.OuterRef("pk"))
        return self.filter(
            models.Exists(tasks.filter(project__provider=provider))
        ).exclude(models.Exists(tasks.exclude(project__provider=provider)))


class Payment(models.Model):
    """A payment received for the tasks of a period (made on the billing page).

    The estimate is what the billing page calculated for the paid tasks; the
    paid values are what was actually received. Deleting a payment makes
    its tasks unpaid again.
    """

    period_start = models.DateField(_("início do período"))
    period_end = models.DateField(_("fim do período"))
    estimated_usd = models.DecimalField(
        _("valor estimado (US$)"), max_digits=12, decimal_places=2
    )
    # None when the exchange rate was unavailable.
    estimated_brl = models.DecimalField(
        _("valor estimado (R$)"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    paid_usd = models.DecimalField(
        _("valor pago (US$)"), max_digits=12, decimal_places=2
    )
    paid_brl = models.DecimalField(
        _("valor pago (R$)"), max_digits=12, decimal_places=2
    )
    created_at = models.DateTimeField(_("registrado em"), auto_now_add=True)

    objects = PaymentQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("pagamento")
        verbose_name_plural = _("pagamentos")

    def __str__(self):
        return gettext("Pagamento de %(start)s a %(end)s") % {
            "start": f"{self.period_start:%d/%m/%Y}",
            "end": f"{self.period_end:%d/%m/%Y}",
        }

    @property
    def provider_name(self):
        """The company of all its tasks' projects; None if there is no such
        single company (needs ``with_task_totals()``)."""
        if self.provider_count == 1 and not self.tasks_without_provider:
            return self.any_provider_name
        return None

    @property
    def mixes_providers(self):
        """Its tasks are of several companies, or of some and of none."""
        return self.provider_count > 1 or bool(
            self.provider_count and self.tasks_without_provider
        )

    @property
    def difference_usd(self):
        """Paid minus estimated: negative when less was received."""
        return self.paid_usd - self.estimated_usd

    @property
    def difference_brl(self):
        """Paid minus estimated, or None without an estimate in reais."""
        if self.estimated_brl is None:
            return None
        return self.paid_brl - self.estimated_brl


class TaskQuerySet(models.QuerySet):
    def started_between(self, start, end):
        """Tasks whose start date is in ``[start, end]``."""
        return self.filter(started_on__range=(start, end))

    def with_statuses(self, statuses):
        return self.filter(status__in=statuses)

    def unpaid(self):
        return self.filter(payment__isnull=True)

    def of_provider(self, provider):
        """Tasks of the provider's projects; every task when it is None."""
        return self if provider is None else self.filter(project__provider=provider)


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
        _("ID externo"),
        max_length=100,
        blank=True,
        help_text=_("Identificador da tarefa no sistema de origem."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Objetivos da tarefa."),
    )
    acceptance_criteria = models.TextField(
        blank=True,
        help_text=_("Como julgar que a tarefa está concluída (como testá-la)."),
    )
    # Whole minutes, so repeated additions stay exact (see domain.durations).
    # The explicit validator keeps full_clean() strict on every Django version
    # (4.2 on SQLite does not add one for PositiveIntegerField).
    minutes_spent = models.PositiveIntegerField(
        default=0,
        help_text=_("Tempo gasto, em minutos."),
        validators=[MinValueValidator(0)],
    )
    started_on = models.DateField(
        default=timezone.localdate,
        help_text=_("Data de criação da tarefa; pode ser corrigida."),
    )
    finished_on = models.DateField(
        null=True,
        blank=True,
        help_text=_(
            "Preenchida ao mudar o status para Review ou Done; pode ser corrigida."
        ),
    )
    status = models.CharField(
        max_length=8,
        choices=TaskStatus.choices,
        default=TaskStatus.DOING,
    )
    # Set when the task is paid (see services.payments); None = not paid.
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name=_("pagamento"),
    )

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ["-started_on", "name"]
        verbose_name = _("tarefa")
        verbose_name_plural = _("tarefas")
        constraints = [
            # An external id identifies one task per project; blank is allowed
            # for any number of tasks.
            models.UniqueConstraint(
                fields=["project", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_task_external_id_per_project",
                violation_error_message=(
                    _("Já existe uma tarefa com este ID externo neste projeto.")
                ),
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.started_on and self.finished_on and self.finished_on < self.started_on:
            raise ValidationError(
                {
                    "finished_on": _(
                        "A data de término não pode ser anterior ao início."
                    )
                }
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
