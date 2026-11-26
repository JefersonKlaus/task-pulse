"""Use case (application layer): Deletes a task that was not billed.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from pulse_core.application import project_or_404, task_or_404
from pulse_core.domain.errors import Conflict
from pulse_core.ports import Dependencies


def delete_task(deps: Dependencies, owner: str, project_id: str, task_id: str) -> None:
    project_or_404(deps, owner, project_id)
    if task_or_404(deps, owner, project_id, task_id).billed:
        raise Conflict("Tarefa já faturada: exclua o pagamento antes")
    deps.repo.delete_tasks(owner, project_id, [task_id])
