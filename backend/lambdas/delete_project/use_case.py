"""Use case (application layer): Deletes a project with its tasks and payments.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from pulse_core.application import project_or_404
from pulse_core.ports import Dependencies


def delete_project(deps: Dependencies, owner: str, id: str) -> None:
    project_or_404(deps, owner, id)
    deps.repo.delete_tasks(owner, id, [t.id for t in deps.repo.list_tasks(owner, id)])
    deps.repo.delete_payments(owner, id, [p.id for p in deps.repo.list_payments(owner, id)])
    deps.repo.delete_project(owner, id)
