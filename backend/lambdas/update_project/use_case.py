"""Use case (application layer): Changes a project's name, company, currency, deadline or description (the rules change on their own routes).
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import company_or_404, now, project_or_404, project_view
from pulse_core.domain.models import Project
from pulse_core.ports import Dependencies


def update_project(deps: Dependencies, owner: str, id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    current = project_or_404(deps, owner, id)
    project = Project.from_input(payload, id, rules=current.rules)
    company = company_or_404(deps, owner, project.company_id)
    deps.repo.save_project(owner, project)
    return project_view(project, company, now())
