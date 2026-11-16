"""Model instance builders shared by the whole test suite.

Every helper has sensible defaults, so a test only spells out the values
that matter for the behaviour it verifies.

* ``create_*`` helpers persist the instance in the database.
* ``build_*`` helpers return an *unsaved* instance, which is what model
  validation tests (``full_clean()``) need.
"""

from datetime import date

from src.models import Project, Task


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
