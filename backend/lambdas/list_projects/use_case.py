"""Use case (application layer): Every project (of one company with ?company_id=), with its company, its rule in force and its open tasks.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from pulse_core.application import now, project_view
from pulse_core.domain.models import DOING
from pulse_core.ports import Dependencies


def list_projects(deps: Dependencies, owner: str, query: Mapping[str, str]) -> list[dict[str, Any]]:
    companies = {c.id: c for c in deps.repo.list_companies(owner)}
    wanted = query.get("company_id")
    open_tasks = Counter(t.project_id for t in deps.repo.list_tasks(owner) if t.status == DOING)
    at = now()
    projects = [p for p in deps.repo.list_projects(owner) if not wanted or p.company_id == wanted]
    views = [{**project_view(p, companies.get(p.company_id), at), "open_tasks": open_tasks[p.id]} for p in projects]
    return sorted(views, key=lambda v: (v["company_name"].casefold(), v["name"].casefold()))
