"""Model instance builders shared by the whole test suite.

Every helper has sensible defaults, so a test only spells out the values
that matter for the behaviour it verifies.

* ``create_*`` helpers persist the instance in the database.
* ``build_*`` helpers return an *unsaved* instance, which is what model
  validation tests (``full_clean()``) need.
"""

from datetime import date
from decimal import Decimal

from src.models import Payment, Project, Provider, Task


def create_provider(name="Alignerr"):
    return Provider.objects.create(name=name)


def build_project(**overrides):
    values = {
        "url": "https://github.com/acme/portal",
        "name": "Projeto",
        "description": "",
    }
    values.update(overrides)
    return Project(**values)


def create_project(**overrides):
    project = build_project(**overrides)
    project.save()
    return project


def task_values(**overrides):
    values = {
        "name": "Tarefa",
        "minutes_spent": 90,
        "started_on": date(2026, 11, 16),
    }
    values.update(overrides)
    return values


def build_task(project=None, **overrides):
    return Task(project=project, **task_values(**overrides))


def create_task(project=None, **overrides):
    return Task.objects.create(
        project=project or create_project(),
        **task_values(**overrides),
    )


def create_payment(*tasks, **overrides):
    """A saved payment; ``tasks`` become paid by it."""
    values = {
        "period_start": date(2026, 11, 1),
        "period_end": date(2026, 11, 30),
        "estimated_usd": Decimal("100.00"),
        "estimated_brl": Decimal("535.00"),
        "paid_usd": Decimal("100.00"),
        "paid_brl": Decimal("530.00"),
    }
    values.update(overrides)
    payment = Payment.objects.create(**values)
    for task in tasks:
        task.payment = payment
        task.save()
    return payment
