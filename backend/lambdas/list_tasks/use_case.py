"""Use case (application layer): Tasks by company, project and period. state=open (default): DOING tasks started up to the end of the period; finished: concluded in the period; all: both.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import period, task_view
from pulse_core.domain.errors import ValidationError
from pulse_core.domain.models import DOING
from pulse_core.ports import Dependencies

STATES = ("open", "finished", "all")


def list_tasks(deps: Dependencies, owner: str, query: Mapping[str, str]) -> dict[str, Any]:
    state = query.get("state") or "open"
    if state not in STATES:
        raise ValidationError("state: open, finished ou all")
    start, end = period(query) if query.get("from") or query.get("to") else ("0000-01-01", "9999-12-31")
    projects = {p.id: p for p in deps.repo.list_projects(owner)
                if (not query.get("company_id") or p.company_id == query["company_id"])
                and (not query.get("project_id") or p.id == query["project_id"])}
    tasks = deps.repo.list_tasks(owner, query["project_id"]) if query.get("project_id") else deps.repo.list_tasks(owner)
    payments = {p.id: p for p in deps.repo.list_payments(owner, query.get("project_id") or None)}

    def wanted(task) -> bool:
        if task.project_id not in projects:
            return False
        is_open = task.status == DOING and task.started_at[:10] <= end
        is_finished = bool(task.finished_at) and start <= task.finished_at[:10] <= end
        return {"open": is_open, "finished": is_finished, "all": is_open or is_finished}[state]

    rows = [task_view(t, projects[t.project_id], payments) for t in tasks if wanted(t)]
    rows.sort(key=lambda r: (r["finished_at"] or r["started_at"]), reverse=True)
    return {"tasks": rows, "totals": {"tasks": len(rows), "minutes": sum(r["minutes"] for r in rows),
                                      "value_cents": sum(r["value_cents"] for r in rows)}}
