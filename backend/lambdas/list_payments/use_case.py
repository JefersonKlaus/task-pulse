"""Use case (application layer): Every payment (of a company or project with ?company_id= / ?project_id=), newest first, with should receive x received.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import payment_view
from pulse_core.ports import Dependencies


def list_payments(deps: Dependencies, owner: str, query: Mapping[str, str]) -> dict[str, Any]:
    companies = {c.id: c for c in deps.repo.list_companies(owner)}
    projects = {p.id: p for p in deps.repo.list_projects(owner)
                if (not query.get("company_id") or p.company_id == query["company_id"])
                and (not query.get("project_id") or p.id == query["project_id"])}
    payments = [p for p in deps.repo.list_payments(owner, query.get("project_id") or None) if p.project_id in projects]
    rows = []
    for payment in sorted(payments, key=lambda p: (p.received_on, p.period_end), reverse=True):
        project = projects[payment.project_id]
        company = companies.get(project.company_id)
        rows.append({**payment_view(payment), "project_name": project.name, "currency": project.currency,
                     "company_id": project.company_id, "company_name": company.name if company else ""})
    return {"payments": rows, "totals": {
        "expected_cents": sum(p.expected_cents for p in payments),
        "received_cents": sum(p.received_cents for p in payments),
        "difference_cents": sum(p.difference_cents for p in payments),
        "not_paid_cents": sum(p.not_paid_cents for p in payments)}}
