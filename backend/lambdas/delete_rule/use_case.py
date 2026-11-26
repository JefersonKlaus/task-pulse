"""Use case (application layer): Deletes a rule no concluded (and not yet billed) task depends on.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from pulse_core.application import now, project_or_404, project_view
from pulse_core.domain.errors import Conflict, NotFound
from pulse_core.ports import Dependencies


def delete_rule(deps: Dependencies, owner: str, project_id: str, rule_id: str) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    rule = next((r for r in project.rules if r.id == rule_id), None)
    if rule is None:
        raise NotFound("regra não encontrada")
    if any(t.finished_at and rule.covers(t.finished_at) and not t.billed
           for t in deps.repo.list_tasks(owner, project_id)):
        raise Conflict("Há tarefas concluídas nesta regra: ela não pode ser excluída")
    project = replace(project, rules=tuple(r for r in project.rules if r.id != rule_id))
    deps.repo.save_project(owner, project)
    return project_view(project, deps.repo.get_company(owner, project.company_id), now())
