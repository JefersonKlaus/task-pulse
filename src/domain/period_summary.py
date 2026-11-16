"""Totals of a list of tasks: hours, per status and (optionally) value.

Each task's value is rounded to cents and the tasks' total is the sum of
the rounded values, so the total always matches the rows shown.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import round_money
from .task_status import TaskStatus


@dataclass(frozen=True)
class TaskLine:
    task: object
    value: Decimal | None  # None without pricing


@dataclass(frozen=True)
class StatusTotal:
    label: str
    tasks: int
    minutes: int


@dataclass(frozen=True)
class PeriodSummary:
    lines: list
    minutes: int
    by_status: list
    # The money fields are None without pricing.
    tasks_usd: Decimal | None  # sum of the task values
    bonus_usd: Decimal | None  # None when no bonus was given
    total_usd: Decimal | None  # tasks + bonus


def summarize(tasks, pricing=None, statuses=tuple(TaskStatus.values)):
    """Summarize ``tasks`` (objects with ``minutes_spent`` and ``status``).

    ``statuses`` lists, in order, the statuses to total (those shown).
    ``pricing`` is a ``Pricing``; without it no value is computed.
    """
    tasks = list(tasks)
    lines = [
        TaskLine(
            task=task,
            value=(
                pricing.task_value(task.minutes_spent, task.status)
                if pricing is not None
                else None
            ),
        )
        for task in tasks
    ]
    by_status = [
        StatusTotal(
            label=TaskStatus(status).label,
            tasks=sum(1 for task in tasks if task.status == status),
            minutes=sum(task.minutes_spent for task in tasks if task.status == status),
        )
        for status in statuses
    ]
    tasks_usd = bonus_usd = total_usd = None
    if pricing is not None:
        tasks_usd = sum((line.value for line in lines), Decimal("0.00"))
        if pricing.bonus is not None:
            bonus_usd = round_money(pricing.bonus)
        total_usd = tasks_usd + (bonus_usd or Decimal("0.00"))
    return PeriodSummary(
        lines=lines,
        minutes=sum(task.minutes_spent for task in tasks),
        by_status=by_status,
        tasks_usd=tasks_usd,
        bonus_usd=bonus_usd,
        total_usd=total_usd,
    )
