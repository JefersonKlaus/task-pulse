"""Use case (application layer): Deletes a company that has no projects.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from pulse_core.application import company_or_404
from pulse_core.domain.errors import Conflict
from pulse_core.ports import Dependencies


def delete_company(deps: Dependencies, owner: str, id: str) -> None:
    company_or_404(deps, owner, id)
    if any(p.company_id == id for p in deps.repo.list_projects(owner)):
        raise Conflict("A empresa tem projetos: exclua ou mova os projetos antes")
    deps.repo.delete_company(owner, id)
