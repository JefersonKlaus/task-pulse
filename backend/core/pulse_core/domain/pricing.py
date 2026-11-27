"""How much a task is worth, by the rule in force when it was finished (see models.Rule).

Hourly, 5h at 90/h with a 100/h flat, approved: 4 x 90 + 1 x 100 = 460. Under an hour, all of it is at
the flat (0:30 -> 50). Not approved (DONE, REJECTED): no flat, 5 x 90 = 450.
Fixed: the fixed amount per task. Every concluded task is paid, rejected ones too (the companies pay for
the work done); with `paid_only_if_approved`, only APPROVED is paid and anything else is 0.
Values are rounded to the cent, half up.
"""
from __future__ import annotations

from typing import Iterable, Optional

from .models import APPROVED, FINISHED, Project, Rule, Task

FLAT_MINUTES = 60           # "the last hour"


def _round_div(numerator: int, denominator: int) -> int:
    return (numerator * 2 + denominator) // (denominator * 2)


def is_paid_status(status: str, rule: Rule) -> bool:
    if rule.paid_only_if_approved:
        return status == APPROVED
    return status in FINISHED                       # DONE, APPROVED and REJECTED


def task_value(task: Task, rule: Optional[Rule]) -> int:
    if rule is None or task.status not in FINISHED or not is_paid_status(task.status, rule):
        return 0
    if rule.kind == "fixed":
        return rule.fixed_cents
    flat_minutes = min(task.minutes, FLAT_MINUTES) if rule.flat_cents and task.status == APPROVED else 0
    amount = (task.minutes - flat_minutes) * rule.hourly_cents + flat_minutes * (rule.flat_cents or 0)
    return _round_div(amount, 60)


def bonus(project: Project, tasks: Iterable[Task]) -> tuple[int, Optional[Rule]]:
    """The bonus for a period: the approved tasks of the period are counted, and the rule in force when
    the last of them was finished says the tiers; the highest tier reached is paid."""
    approved = sorted((t for t in tasks if t.status == APPROVED and t.finished_at), key=lambda t: t.finished_at)
    if not approved:
        return 0, None
    rule = project.rule_at(approved[-1].finished_at)
    if rule is None:
        return 0, None
    reached = [tier.bonus_cents for tier in rule.bonus_tiers if len(approved) >= tier.min_tasks]
    return (reached[-1] if reached else 0), rule
