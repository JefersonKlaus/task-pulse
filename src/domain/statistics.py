"""Statistics of a period, month by month or week by week.

* A task counts in the month or week of its start date ("Início"), as on
  the billing page. Its hours are paid or unpaid (whether it is in a
  payment).
* Money is what was received: a payment's "Pago (US$)" counts in the month
  or week it was registered.
* The average rate is the money received divided by the hours of the
  tasks those payments paid.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .money import round_money
from .task_status import TaskStatus


@dataclass(frozen=True)
class TaskRecord:
    started_on: date
    minutes: int
    status: str
    paid: bool
    project: str
    provider: str | None = None  # the project's company, if it has one


@dataclass(frozen=True)
class PaymentRecord:
    registered_on: date
    paid_usd: Decimal
    minutes: int  # of its tasks


@dataclass(frozen=True)
class BucketStatistics:
    """The numbers of one month or week."""

    bucket: object  # periods.Bucket
    minutes: int
    paid_minutes: int
    tasks_by_status: dict  # status -> number of tasks, every status
    received_usd: Decimal

    @property
    def unpaid_minutes(self):
        return self.minutes - self.paid_minutes

    @property
    def tasks(self):
        return sum(self.tasks_by_status.values())


@dataclass(frozen=True)
class Statistics:
    buckets: list  # of BucketStatistics, in order
    minutes_by_project: dict  # project name -> minutes, only those with tasks
    # company name (None: projects without one) -> minutes, likewise
    minutes_by_provider: dict
    payments: int
    payments_minutes: int  # hours of the tasks of those payments

    @property
    def minutes(self):
        return sum(bucket.minutes for bucket in self.buckets)

    @property
    def paid_minutes(self):
        return sum(bucket.paid_minutes for bucket in self.buckets)

    @property
    def unpaid_minutes(self):
        return self.minutes - self.paid_minutes

    @property
    def tasks(self):
        return sum(bucket.tasks for bucket in self.buckets)

    @property
    def done_tasks(self):
        return sum(bucket.tasks_by_status[TaskStatus.DONE] for bucket in self.buckets)

    @property
    def received_usd(self):
        return sum((bucket.received_usd for bucket in self.buckets), Decimal("0.00"))

    @property
    def average_hourly_usd(self):
        """Received per hour paid; None without paid hours."""
        if not self.payments_minutes:
            return None
        return round_money(self.received_usd * 60 / self.payments_minutes)

    @property
    def empty(self):
        return not self.tasks and not self.payments


def compute_statistics(buckets, tasks, payments):
    """``tasks`` and ``payments`` (records) fall in ``buckets`` by date.

    Records outside every bucket are ignored.
    """
    per_bucket = [
        {
            "minutes": 0,
            "paid_minutes": 0,
            "tasks_by_status": dict.fromkeys(TaskStatus.values, 0),
            "received_usd": Decimal("0.00"),
        }
        for _ in buckets
    ]
    minutes_by_project, minutes_by_provider = {}, {}
    counted_payments = payments_minutes = 0

    for task in tasks:
        totals = _totals_of(task.started_on, buckets, per_bucket)
        if totals is None:
            continue
        totals["minutes"] += task.minutes
        totals["paid_minutes"] += task.minutes if task.paid else 0
        totals["tasks_by_status"][task.status] += 1
        minutes_by_project[task.project] = (
            minutes_by_project.get(task.project, 0) + task.minutes
        )
        minutes_by_provider[task.provider] = (
            minutes_by_provider.get(task.provider, 0) + task.minutes
        )

    for payment in payments:
        totals = _totals_of(payment.registered_on, buckets, per_bucket)
        if totals is None:
            continue
        totals["received_usd"] += payment.paid_usd
        counted_payments += 1
        payments_minutes += payment.minutes

    return Statistics(
        buckets=[
            BucketStatistics(bucket=bucket, **totals)
            for bucket, totals in zip(buckets, per_bucket)
        ],
        minutes_by_project=minutes_by_project,
        minutes_by_provider=minutes_by_provider,
        payments=counted_payments,
        payments_minutes=payments_minutes,
    )


def _totals_of(day, buckets, per_bucket):
    for bucket, totals in zip(buckets, per_bucket):
        if day in bucket:
            return totals
    return None
