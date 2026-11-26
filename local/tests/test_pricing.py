"""What a task is worth, by its rule (pure domain, no repository)."""
import pytest

from pulse_core.domain.errors import ValidationError
from pulse_core.domain.models import Project, Rule, Task
from pulse_core.domain.pricing import bonus, task_value

from conftest import fixed, hourly


def task(status="APPROVED", minutes=300, finished_at="2026-11-10T10:00", id="t"):
    return Task(id, "p", "x", "2026-11-01T09:00", status, finished_at if status != "DOING" else None, minutes)


@pytest.mark.parametrize("status, minutes, expected", [
    ("APPROVED", 300, 46000),      # 4h x 90 + the last hour x 100
    ("APPROVED", 30, 5000),        # under an hour: all of it at the flat
    ("DONE", 300, 45000),          # not approved: no flat
    ("REJECTED", 300, 0),          # rejected: never paid
    ("DOING", 300, 0),             # not concluded: nothing yet
    ("APPROVED", 61, 10150),       # 1 min x 90 + 60 min x 100 = 101,50
])
def test_hourly_with_flat_last_hour(status, minutes, expected):
    rule = Rule.from_input(hourly(flat_cents=10000))
    assert task_value(task(status, minutes), rule) == expected


def test_hourly_without_flat_and_rounding():
    rule = Rule.from_input(hourly(hourly_cents=10001))
    assert task_value(task("APPROVED", 1), rule) == 167          # 100,01 / 60 = 1,6668 -> 1,67


def test_paid_only_if_approved():
    rule = Rule.from_input(hourly(paid_only_if_approved=True))
    assert task_value(task("DONE"), rule) == 0
    assert task_value(task("APPROVED"), rule) == 45000


def test_fixed_per_task_whatever_the_time():
    rule = Rule.from_input(fixed())
    assert task_value(task("DONE", 5), rule) == 35000
    assert task_value(task("APPROVED", 900), rule) == 35000
    assert task_value(task("REJECTED"), rule) == 0
    assert task_value(task("DONE"), Rule.from_input(fixed(paid_only_if_approved=True))) == 0


def test_no_rule_is_worth_nothing():
    assert task_value(task(), None) == 0


def test_bonus_highest_tier_by_approved_tasks_of_the_rule_in_force():
    rule = Rule.from_input(hourly(bonus_tiers=[{"min_tasks": 5, "bonus_cents": 9000},
                                               {"min_tasks": 2, "bonus_cents": 1000}]))
    project = Project("p", "c", "P", rules=(rule,))
    assert bonus(project, [task(id="a")])[0] == 0
    assert bonus(project, [task(id="a"), task(id="b"), task("DONE", id="c")])[0] == 1000
    assert bonus(project, [task(id=str(i)) for i in range(5)])[0] == 9000


@pytest.mark.parametrize("payload, message", [
    ({"kind": "x"}, "Tipo"),
    (hourly(hourly_cents=0), "maior que zero"),
    (hourly(hourly_cents=10.5), "inválido"),
    (hourly(ends_at="2025-01-01T00:00"), "depois do início"),
    (fixed(fixed_cents=None), "obrigatório"),
    (hourly(bonus_tiers=[{"min_tasks": 2, "bonus_cents": 1}, {"min_tasks": 2, "bonus_cents": 3}]), "diferente"),
])
def test_rule_validation(payload, message):
    with pytest.raises(ValidationError, match=message):
        Rule.from_input(payload)


def test_rule_covers_from_start_until_end_excluded():
    rule = Rule.from_input(hourly(starts_at="2026-11-10T14:00", ends_at="2026-11-11T14:00"))
    assert not rule.covers("2026-11-10T13:59")
    assert rule.covers("2026-11-10T14:00")
    assert rule.covers("2026-11-11T13:59")
    assert not rule.covers("2026-11-11T14:00")
