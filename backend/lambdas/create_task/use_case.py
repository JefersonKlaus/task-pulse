"""Use case (application layer): Adds a task: name, external id, repository, description, start; concluded already, with the time and the finish.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import MAX_TASKS, check_unique_external_id, now, project_or_404, task_view
from pulse_core.domain.errors import ValidationError
from pulse_core.domain.models import Task
from pulse_core.ports import Dependencies


def create_task(deps: Dependencies, owner: str, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    task = Task.from_input(payload, project.id, now())
    if len(deps.repo.list_tasks(owner, project.id)) >= MAX_TASKS:
        raise ValidationError(f"Limite de {MAX_TASKS} tarefas por projeto")
    check_unique_external_id(deps, owner, task)
    deps.repo.save_tasks(owner, [task])
    return task_view(task, project)
