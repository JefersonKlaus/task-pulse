"""Use case (application layer): Changes a task (only the fields sent). Concluding it without a finish takes this moment.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import check_unique_external_id, now, project_or_404, task_or_404, task_view
from pulse_core.ports import Dependencies


def update_task(deps: Dependencies, owner: str, project_id: str, task_id: str,
                payload: Mapping[str, Any]) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    task = task_or_404(deps, owner, project_id, task_id).edited(payload, now())
    check_unique_external_id(deps, owner, task)
    deps.repo.save_tasks(owner, [task])
    payments = {p.id: p for p in deps.repo.list_payments(owner, project_id)} if task.billed else {}
    return task_view(task, project, payments)
