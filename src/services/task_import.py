"""Import parsed CSV rows as tasks of a project.

* A row whose id already belongs to a task in the project is skipped: that
  task is left exactly as it is, and the row is not imported again.
* The file's date is the start date, and also the finish date unless the
  task is DOING.
* A desc longer than a task name is shortened; the full text is kept as the
  description.
* Everything runs in one transaction: if anything fails, neither the new
  project nor any task is saved.
"""

from dataclasses import dataclass

from django.db import transaction

from ..domain.task_status import TaskStatus
from ..models import Project, Task

NAME_MAX_LENGTH = Task._meta.get_field("name").max_length


@dataclass(frozen=True)
class NewProject:
    """A project to create for the import (name optional, as usual)."""

    url: str
    name: str = ""


@dataclass(frozen=True)
class ImportResult:
    created: int
    skipped: int

    @property
    def total(self):
        return self.created + self.skipped


@transaction.atomic
def import_tasks(rows, destination):
    """Import ``rows`` into ``destination`` (a ``Project`` or ``NewProject``).

    Returns ``(project, ImportResult)``.
    """
    project = (
        destination
        if isinstance(destination, Project)
        else _create_project(destination)
    )
    return project, import_rows(project, rows)


def import_rows(project, rows):
    """Create the project's tasks from ``rows``, skipping known ids."""
    existing_ids = set(
        project.tasks.filter(
            external_id__in=[row.external_id for row in rows]
        ).values_list("external_id", flat=True)
    )
    created = skipped = 0
    for row in rows:
        if row.external_id in existing_ids:
            skipped += 1
            continue
        task = _build_task(project, row)
        task.full_clean()
        task.save()
        created += 1
    return ImportResult(created=created, skipped=skipped)


def _create_project(new_project):
    project = Project(url=new_project.url, name=new_project.name)
    project.full_clean()
    project.save()
    return project


def _build_task(project, row):
    name, full_description = _split_desc(row.desc)
    return Task(
        project=project,
        external_id=row.external_id,
        name=name,
        description=full_description,
        status=row.status,
        started_on=row.date,
        finished_on=None if row.status == TaskStatus.DOING else row.date,
        minutes_spent=row.minutes,
    )


def _split_desc(desc):
    if len(desc) <= NAME_MAX_LENGTH:
        return desc, ""
    return desc[: NAME_MAX_LENGTH - 1] + "…", desc
