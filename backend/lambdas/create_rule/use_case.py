"""Use case (application layer): Adds a pricing rule from a moment on. A rule still open (no end) that started before is closed when the new one starts.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from pulse_core.application import now, project_or_404, project_view
from pulse_core.domain.errors import ValidationError
from pulse_core.domain.models import Rule
from pulse_core.ports import Dependencies

MAX_RULES = 200


def create_rule(deps: Dependencies, owner: str, project_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    rule = Rule.from_input(payload)
    if len(project.rules) >= MAX_RULES:
        raise ValidationError(f"Limite de {MAX_RULES} regras por projeto")
    rules = []
    for other in project.rules:
        if other.ends_at is None and other.starts_at < rule.starts_at:
            other = replace(other, ends_at=rule.starts_at)       # the new values start where the old ones end
        if rule.overlaps(other):
            raise ValidationError("Já existe uma regra nesse intervalo: as regras não podem se sobrepor")
        rules.append(other)
    project = replace(project, rules=tuple(rules) + (rule,))
    deps.repo.save_project(owner, project)
    return project_view(project, deps.repo.get_company(owner, project.company_id), now())
