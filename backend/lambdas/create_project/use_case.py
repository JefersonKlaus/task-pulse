"""Use case (application layer): Registers a project of a company: name, currency, deadline and, optionally, its first pricing rule (`rule`).
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import MAX_PROJECTS, company_or_404, now, project_view
from pulse_core.domain.errors import ValidationError
from pulse_core.domain.models import Project, Rule
from pulse_core.ports import Dependencies


def create_project(deps: Dependencies, owner: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    rule = payload.get("rule")
    rules = (Rule.from_input(rule),) if isinstance(rule, Mapping) else ()
    project = Project.from_input(payload, rules=rules)
    company = company_or_404(deps, owner, project.company_id)
    if len(deps.repo.list_projects(owner)) >= MAX_PROJECTS:
        raise ValidationError(f"Limite de {MAX_PROJECTS} projetos")
    deps.repo.save_project(owner, project)
    return project_view(project, company, now())
