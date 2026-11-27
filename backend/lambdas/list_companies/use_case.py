"""Use case (application layer): Every company of the user, by name, with how many projects and open tasks
it has. A well-known company comes with the catalog's name and notes (`known`: true); one registered by
hand with a well-known name is adopted first (application.adopt_known_companies).
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from collections import Counter
from typing import Any

from pulse_core.application import adopt_known_companies, companies
from pulse_core.domain.models import DOING
from pulse_core.ports import Dependencies


def list_companies(deps: Dependencies, owner: str) -> list[dict[str, Any]]:
    adopt_known_companies(deps, owner)
    projects = deps.repo.list_projects(owner)
    company_of = {p.id: p.company_id for p in projects}
    project_count = Counter(p.company_id for p in projects)
    open_tasks = Counter(company_of.get(t.project_id) for t in deps.repo.list_tasks(owner) if t.status == DOING)
    return [{**c.to_dict(), "projects": project_count[c.id], "open_tasks": open_tasks[c.id]}
            for c in sorted(companies(deps, owner), key=lambda c: c.name.casefold())]
