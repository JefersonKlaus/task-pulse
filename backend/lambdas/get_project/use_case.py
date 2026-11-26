"""Use case (application layer): One project with its company and every pricing rule.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any

from pulse_core.application import now, project_or_404, project_view
from pulse_core.ports import Dependencies


def get_project(deps: Dependencies, owner: str, id: str) -> dict[str, Any]:
    project = project_or_404(deps, owner, id)
    return project_view(project, deps.repo.get_company(owner, project.company_id), now())
