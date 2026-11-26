"""Demo data for the local server, always dated around today: two companies, three projects (hourly with
a flat last hour and a bonus, hourly whose rate changed last week, fixed per task) and their tasks, some
open, some concluded, some already paid. Goes through the same use cases as the API."""
from __future__ import annotations

from datetime import date, timedelta

from create_company.use_case import create_company
from create_payment.use_case import create_payment
from create_project.use_case import create_project
from create_rule.use_case import create_rule
from create_task.use_case import create_task
from pulse_core.ports import Dependencies


def seed(deps: Dependencies, owner: str, today: date) -> None:
    def at(days_ago: int, hour: int = 10) -> str:
        return f"{(today - timedelta(days=days_ago)).isoformat()}T{hour:02d}:00"

    start = at(120, 0)
    acme = create_company(deps, owner, {"name": "Alignerr"})
    etho = create_company(deps, owner, {"name": "Etho"})

    review = create_project(deps, owner, {
        "company_id": acme["id"], "name": "Code review", "currency": "USD",
        "deadline": (today + timedelta(days=60)).isoformat(),
        "rule": {"kind": "hourly", "starts_at": start, "hourly_cents": 9000, "flat_cents": 10000,
                 "paid_only_if_approved": True,
                 "bonus_tiers": [{"min_tasks": 3, "bonus_cents": 5000}, {"min_tasks": 6, "bonus_cents": 15000}]}})
    api = create_project(deps, owner, {
        "company_id": acme["id"], "name": "API de pagamentos", "currency": "USD",
        "rule": {"kind": "hourly", "starts_at": start, "hourly_cents": 6000}})
    create_rule(deps, owner, api["id"], {"kind": "hourly", "starts_at": at(7, 0), "hourly_cents": 7500})
    portal = create_project(deps, owner, {
        "company_id": etho["id"], "name": "Portal do cliente", "currency": "BRL",
        "rule": {"kind": "fixed", "starts_at": start, "fixed_cents": 35000}})

    def task(project, name, days_ago, status="DOING", minutes=0, finished_days_ago=None, **extra):
        payload = {"name": name, "started_at": at(days_ago, 9), "status": status, "minutes": minutes, **extra}
        if status != "DOING":
            payload["finished_at"] = at(finished_days_ago if finished_days_ago is not None else days_ago, 17)
        return create_task(deps, owner, project["id"], payload)

    old = today.replace(day=1) - timedelta(days=1)          # last month: billed already
    task(review, "Revisar PR de autenticação", (today - old).days + 10, "APPROVED", 300,
         external_id="CR-90", repository="acme/portal")
    task(review, "Revisar migração do banco", (today - old).days + 5, "REJECTED", 90, external_id="CR-91")
    create_payment(deps, owner, review["id"], {
        "period_start": old.replace(day=1).isoformat(), "period_end": old.isoformat(),
        "received_cents": 46000, "received_on": today.replace(day=1).isoformat()})

    for i, (status, minutes) in enumerate([("APPROVED", 300), ("APPROVED", 45), ("APPROVED", 150), ("DONE", 120)]):
        task(review, f"Revisão #{101 + i}", min(i + 1, today.day - 1) if today.day > 1 else 0, status, minutes,
             external_id=f"CR-{101 + i}", repository="acme/backend")
    task(review, "Revisar refatoração do checkout", 0, external_id="CR-110", repository="acme/checkout",
         description="Conferir os testes e a cobertura")
    task(api, "Webhook de estorno", 10, "DONE", 240, finished_days_ago=9, repository="acme/payments")
    task(api, "Idempotência nos pagamentos", 3, "DONE", 180, finished_days_ago=2, repository="acme/payments")
    task(api, "Fila de reprocessamento", 1, repository="acme/payments")
    task(portal, "Tela de login", 6, "APPROVED", 200, finished_days_ago=5, repository="etho/portal")
    task(portal, "Página de faturas", 2, repository="etho/portal")
