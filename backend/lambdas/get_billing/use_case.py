"""Use case (application layer): The billing of a project for ?from=&to=: every task concluded in it, its value, paid / not paid / open, the bonus and the totals (should receive, received).
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import billing, period, project_or_404
from pulse_core.ports import Dependencies


def get_billing(deps: Dependencies, owner: str, project_id: str, query: Mapping[str, str]) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    start, end = period(query)
    return billing(deps, owner, project, start, end)
