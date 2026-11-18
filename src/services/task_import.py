"""Import parsed CSV rows as tasks of their projects.

* A row with a github repository goes to that repository's project: the
  existing one whose URL is the same repository (however written; the
  oldest if there are several), or a new one, named after the repository.
* A row without github goes to the destination chosen in the form, which
  is only needed (and a new one only created) when there are such rows.
* Projects created by the import belong to ``provider`` (a company, or
  None); existing projects keep theirs.
* A row whose id already belongs to a task in its project is skipped: that
  task is left exactly as it is, and the row is not imported again.
* The file's date is the start date, and also the finish date unless the
  task is DOING.
* A desc longer than a task name is shortened; the full text is kept as the
  description.
* Everything runs in one transaction: if anything fails, no new project
  and no task is saved.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from ..domain.git_urls import repository_key
from ..domain.task_status import TaskStatus
from ..models import Project, Provider, Task

NAME_MAX_LENGTH = Task._meta.get_field("name").max_length


@dataclass(frozen=True)
class NewProject:
    """A project to create for the import (name optional, as usual)."""

    url: str
    name: str = ""
    provider: Provider | None = None


@dataclass(frozen=True)
class ImportResult:
    created: int
    skipped: int

    @property
    def total(self):
        return self.created + self.skipped


@dataclass(frozen=True)
class ProjectImport:
    """What the import did in one project."""

    project: Project
    result: ImportResult
    new: bool  # the import created the project


@transaction.atomic
def import_tasks(rows, destination=None, provider=None):
    """Import ``rows`` into their projects.

    ``destination`` (a ``Project`` or a ``NewProject``) receives the rows
    without github; it may be None when every row has one. Projects created
    for a github repository belong to ``provider``.
    Returns a ``ProjectImport`` per project, in the order of the file.
    """
    by_repository = _projects_by_repository()
    new_projects = set()
    default = None
    if any(not row.github for row in rows):
        default = _resolve(destination, new_projects)
        # Rows naming the same repository join it instead of creating another.
        by_repository.setdefault(repository_key(default.url), default)

    rows_by_project = {}
    for row in rows:
        project = default
        if row.github:
            key = repository_key(row.github)
            if key not in by_repository:
                new_project = NewProject(url=row.github, provider=provider)
                by_repository[key] = _resolve(new_project, new_projects)
            project = by_repository[key]
        rows_by_project.setdefault(project, []).append(row)

    return [
        ProjectImport(project, import_rows(project, group), project in new_projects)
        for project, group in rows_by_project.items()
    ]


def creates_projects(rows, destination=None):
    """Whether importing ``rows`` creates a project: the ``NewProject``
    destination of rows without github, or a github repository that no
    project has yet."""
    if isinstance(destination, NewProject) and any(not row.github for row in rows):
        return True
    known = _projects_by_repository()
    return any(row.github and repository_key(row.github) not in known for row in rows)


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


def _projects_by_repository():
    """Existing projects by ``repository_key`` of their URL; the oldest wins."""
    projects = {}
    for project in Project.objects.order_by("pk"):
        projects.setdefault(repository_key(project.url), project)
    projects.pop(None, None)  # URLs that aren't a repository never match
    return projects


def _resolve(destination, new_projects):
    """``destination`` itself, or the project created from a ``NewProject``."""
    if isinstance(destination, Project):
        return destination
    project = Project(
        url=destination.url, name=destination.name, provider=destination.provider
    )
    project.full_clean()
    project.save()
    new_projects.add(project)
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
