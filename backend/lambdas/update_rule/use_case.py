"""Use case (application layer): Changes a rule. Once a task finished under it, only its end can change (and not to before that task): to change the values, create a new rule from now on.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from pulse_core.application import company, now, project_or_404, project_view
from pulse_core.domain.errors import NotFound, ValidationError
from pulse_core.domain.models import Rule
from pulse_core.ports import Dependencies


def update_rule(deps: Dependencies, owner: str, project_id: str, rule_id: str,
                payload: Mapping[str, Any]) -> dict[str, Any]:
    project = project_or_404(deps, owner, project_id)
    current = next((r for r in project.rules if r.id == rule_id), None)
    if current is None:
        raise NotFound("regra não encontrada")
    rule = Rule.from_input(payload, rule_id)
    used = [t for t in deps.repo.list_tasks(owner, project_id)
            if t.finished_at and current.covers(t.finished_at) and not t.billed]
    if used:
        if not rule.same_pricing(current):
            raise ValidationError("Já há tarefas concluídas nesta regra: para mudar os valores, crie uma nova "
                                  "regra a partir de agora (esta é encerrada quando a nova começa)")
        last = max(t.finished_at for t in used)
        if rule.ends_at is not None and rule.ends_at <= last:
            raise ValidationError(f"Já há tarefa concluída nesta regra em {last}: o fim deve ser depois disso")
    others = [r for r in project.rules if r.id != rule_id]
    for other in others:
        if rule.overlaps(other):
            raise ValidationError("Já existe uma regra nesse intervalo: as regras não podem se sobrepor")
    project = replace(project, rules=tuple(others) + (rule,))
    deps.repo.save_project(owner, project)
    return project_view(project, company(deps, owner, project.company_id), now())
