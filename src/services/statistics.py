"""Build the Estatísticas page: hours, tasks and money of a period.

The rules are in ``domain.statistics``; this module reads the tasks started
in the period and the payments registered in it, of one company
(``provider``) or of all.
"""

from __future__ import annotations

from datetime import date

from django.utils import timezone

from ..domain.periods import buckets
from ..domain.statistics import (
    PaymentRecord,
    Statistics,
    TaskRecord,
    compute_statistics,
)
from ..models import Payment, Provider, Task


def build_statistics(
    *, start: date, end: date, grouping: str, provider: Provider | None = None
) -> Statistics:
    tasks = (
        Task.objects.started_between(start, end)
        .of_provider(provider)
        .select_related("project__provider")
        .only(
            "started_on",
            "minutes_spent",
            "status",
            "payment_id",
            "project__name",
            "project__provider__name",
        )
    )
    # __date is the registration day in the app's time zone.
    payments = (
        Payment.objects.of_provider(provider)
        .with_task_totals()
        .filter(created_at__date__range=(start, end))
    )
    return compute_statistics(
        buckets(start, end, grouping),
        tasks=[
            TaskRecord(
                started_on=task.started_on,
                minutes=task.minutes_spent,
                status=task.status,
                paid=task.payment_id is not None,
                project=task.project.name,
                provider=task.project.provider and task.project.provider.name,
            )
            for task in tasks
        ],
        payments=[
            PaymentRecord(
                registered_on=timezone.localtime(payment.created_at).date(),
                paid_usd=payment.paid_usd,
                minutes=payment.minutes,
            )
            for payment in payments
        ],
    )
