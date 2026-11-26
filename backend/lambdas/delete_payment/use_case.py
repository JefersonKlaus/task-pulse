"""Use case (application layer): Deletes a payment: its tasks are open again.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from dataclasses import replace

from pulse_core.application import project_or_404
from pulse_core.domain.errors import NotFound
from pulse_core.ports import Dependencies


def delete_payment(deps: Dependencies, owner: str, project_id: str, payment_id: str) -> None:
    project_or_404(deps, owner, project_id)
    if deps.repo.get_payment(owner, project_id, payment_id) is None:
        raise NotFound("pagamento não encontrado")
    tasks = [replace(t, billing="", payment_id=None) for t in deps.repo.list_tasks(owner, project_id)
             if t.payment_id == payment_id]
    if tasks:
        deps.repo.save_tasks(owner, tasks)
    deps.repo.delete_payments(owner, project_id, [payment_id])
