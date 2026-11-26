"""Use case (application layer): Registers what was received for a period: every open task concluded in it is paid, except `not_paid_task_ids`. Answers the billing of that period.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import billing, project_or_404, register_payment
from pulse_core.ports import Dependencies


def create_payment(deps: Dependencies, owner: str, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    payment = register_payment(deps, owner, project, payload)
    return billing(deps, owner, project, payment.period_start, payment.period_end)
