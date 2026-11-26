"""Use case (application layer): Adds time worked to a task (`minutes`); with `finish`, concludes it now (or at `finished_at`).
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import now, project_or_404, task_or_404, task_view
from pulse_core.domain.models import flag, minutes, moment
from pulse_core.ports import Dependencies


def add_task_time(deps: Dependencies, owner: str, project_id: str, task_id: str,
                  payload: Mapping[str, Any]) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    task = task_or_404(deps, owner, project_id, task_id).with_time(
        minutes(payload, "minutes"), now(), flag(payload, "finish"),
        moment(payload.get("finished_at"), "Término", required=False))
    deps.repo.save_tasks(owner, [task])
    return task_view(task, project)
