"""Rules shared by several use cases: the clock, lookups, limits, what the screens receive, and the
billing of a period. Depends only on the domain and the ports, never on AWS."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Optional

from .domain.catalog import known_by_name, resolve
from .domain.errors import NotFound, ValidationError
from .domain.models import NOT_PAID, PAID, Company, Payment, Project, Task, cents, day, new_id, text
from .domain.pricing import bonus, task_value
from .ports import Dependencies

BRASILIA = timezone(timedelta(hours=-3))       # no daylight saving time since 2019
MAX_COMPANIES, MAX_PROJECTS, MAX_TASKS = 200, 500, 20_000
MAX_PERIOD_DAYS = 400


def now() -> str:
    """This moment in Brasília, "YYYY-MM-DDTHH:MM"."""
    return datetime.now(BRASILIA).strftime("%Y-%m-%dT%H:%M")


def today() -> str:
    return now()[:10]


# ------------------------------------------------------------------ lookups
def companies(deps: Dependencies, owner: str) -> list[Company]:
    """The user's companies as they are shown: a well-known one with the catalog's name and notes."""
    return [resolve(c) for c in deps.repo.list_companies(owner)]


def company(deps: Dependencies, owner: str, id: Optional[str]) -> Optional[Company]:
    found = deps.repo.get_company(owner, id) if id else None
    return resolve(found) if found else None


def company_or_404(deps: Dependencies, owner: str, id: Optional[str]) -> Company:
    found = company(deps, owner, id)
    if found is None:
        raise NotFound("empresa não encontrada")
    return found


def adopt_known_companies(deps: Dependencies, owner: str) -> None:
    """A company the user registered by hand with the name of a well-known one (before they existed)
    becomes the well-known one: its projects move to it and the hand-made record goes. Runs when the
    companies are listed, and does nothing once there is nothing left to adopt."""
    mine = deps.repo.list_companies(owner)
    chosen = {c.id for c in mine if c.known}
    for own in [c for c in mine if not c.known]:
        known = known_by_name(own.name)
        if known is None:
            continue
        if known.id not in chosen:
            deps.repo.save_company(owner, known)
            chosen.add(known.id)
        for project in deps.repo.list_projects(owner):
            if project.company_id == own.id:
                deps.repo.save_project(owner, replace(project, company_id=known.id))
        deps.repo.delete_company(owner, own.id)


def project_or_404(deps: Dependencies, owner: str, id: Optional[str]) -> Project:
    project = deps.repo.get_project(owner, id) if id else None
    if project is None:
        raise NotFound("projeto não encontrado")
    return project


def task_or_404(deps: Dependencies, owner: str, project_id: str, id: Optional[str]) -> Task:
    task = deps.repo.get_task(owner, project_id, id) if id else None
    if task is None:
        raise NotFound("tarefa não encontrada")
    return task


def check_unique_company_name(deps: Dependencies, owner: str, company: Company) -> None:
    for other in companies(deps, owner):
        if other.id != company.id and other.name.casefold() == company.name.casefold():
            raise ValidationError("Já existe uma empresa com este nome")


def check_unique_external_id(deps: Dependencies, owner: str, task: Task) -> None:
    if not task.external_id:
        return
    for other in deps.repo.list_tasks(owner, task.project_id):
        if other.id != task.id and other.external_id.casefold() == task.external_id.casefold():
            raise ValidationError("Já existe uma tarefa com este ID externo neste projeto")


def period(query: Mapping[str, str], start_key: str = "from", end_key: str = "to") -> tuple[str, str]:
    start = day(query.get(start_key), "Início do período")
    end = day(query.get(end_key), "Fim do período")
    if end < start:
        raise ValidationError("O fim do período deve ser depois do início")
    if (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days > MAX_PERIOD_DAYS:
        raise ValidationError(f"Período de no máximo {MAX_PERIOD_DAYS} dias")
    return start, end


# ------------------------------------------------------------------ what the screens receive
def project_view(project: Project, company: Optional[Company], at: str) -> dict[str, Any]:
    """The project with its company's name, the rule in force at `at`, and each deadline with its next
    day from `at` (`next_on`; None for a day that has passed) plus the nearest one (`next_deadline`)."""
    rule = project.rule_at(at)
    today_ = at[:10]
    nearest = project.next_deadline(today_)
    return {**project.to_dict(), "company_name": company.name if company else "",
            "company_known": bool(company and company.known),
            "current_rule_id": rule.id if rule else None,
            "deadlines": [{**d.to_dict(), "next_on": d.next_on(today_)} for d in project.deadlines],
            "next_deadline": {**nearest[1].to_dict(), "next_on": nearest[0]} if nearest else None}


def task_view(task: Task, project: Project, payments: Mapping[str, Payment] = {}) -> dict[str, Any]:
    """The task, what it is worth and by which rule. A billed task is worth what its payment froze."""
    payment = payments.get(task.payment_id or "")
    lost = 0
    if payment is not None:
        value = payment.task_values.get(task.id, 0)
        lost = payment.not_paid_values.get(task.id, 0)
        rule_id = None
    else:
        rule = project.rule_at(task.finished_at)
        value, rule_id = task_value(task, rule), (rule.id if rule else None)
    return {**task.to_dict(), "value_cents": value, "lost_cents": lost, "rule_id": rule_id, "project_name": project.name,
            "company_id": project.company_id, "currency": project.currency}


# ------------------------------------------------------------------ billing
def finished_in(tasks: Iterable[Task], start: str, end: str) -> list[Task]:
    return [t for t in tasks if t.finished and t.finished_at and start <= t.finished_at[:10] <= end]


def overlapping_payments(payments: Iterable[Payment], start: str, end: str) -> list[Payment]:
    return [p for p in payments if p.period_start <= end and start <= p.period_end]


def billing(deps: Dependencies, owner: str, project: Project, start: str, end: str) -> dict[str, Any]:
    """Every task finished in [start, end], what each is worth and how it stands (paid, not paid, open),
    the period's bonus, and the totals: what should be received, what was received, what is still open."""
    all_payments = deps.repo.list_payments(owner, project.id)
    by_id = {p.id: p for p in all_payments}
    tasks = sorted(finished_in(deps.repo.list_tasks(owner, project.id), start, end),
                   key=lambda t: (t.finished_at or "", t.name))
    rows = [task_view(t, project, by_id) for t in tasks]
    open_rows = [r for r in rows if not r["payment_id"]]
    bonus_cents, bonus_rule = bonus(project, tasks)
    payments = overlapping_payments(all_payments, start, end)
    bonus_paid = sum(p.bonus_cents for p in payments)
    bonus_due = max(0, bonus_cents - bonus_paid)
    paid_value = sum(r["value_cents"] for r in rows if r["billing"] == PAID)
    not_paid_value = sum(r["lost_cents"] for r in rows if r["billing"] == NOT_PAID)
    open_value = sum(r["value_cents"] for r in open_rows)
    received = sum(p.received_cents for p in payments)
    expected_paid = sum(p.expected_cents for p in payments)
    return {
        "project": project.to_dict(), "period": {"from": start, "to": end},
        "tasks": rows,
        "payments": [payment_view(p)
                     for p in sorted(payments, key=lambda p: p.received_on, reverse=True)],
        "bonus": {"cents": bonus_cents, "paid_cents": min(bonus_paid, bonus_cents), "due_cents": bonus_due,
                  "approved_tasks": sum(1 for t in tasks if t.status == "APPROVED"),
                  "rule_id": bonus_rule.id if bonus_rule else None},
        "totals": {
            "tasks": len(rows), "minutes": sum(t.minutes for t in tasks),
            "paid_tasks": sum(1 for r in rows if r["billing"] == PAID),
            "not_paid_tasks": sum(1 for r in rows if r["billing"] == NOT_PAID),
            "open_tasks": len(open_rows),
            "paid_value_cents": paid_value, "not_paid_value_cents": not_paid_value,
            "open_value_cents": open_value,
            "to_receive_cents": open_value + bonus_due,
            "expected_cents": expected_paid + open_value + bonus_due,
            "received_cents": received,
            "difference_cents": received - expected_paid,
        },
    }


def payment_view(payment: Payment) -> dict[str, Any]:
    return {**payment.to_dict(), "difference_cents": payment.difference_cents,
            "not_paid_cents": payment.not_paid_cents, "paid_tasks": len(payment.task_values),
            "not_paid_tasks": len(payment.not_paid_values)}


def register_payment(deps: Dependencies, owner: str, project: Project, payload: Mapping[str, Any]) -> Payment:
    """Closes a period: every open task finished in it is marked paid, except the ones in
    `not_paid_task_ids`; the value of each task is frozen in the payment."""
    start, end = period(payload, "period_start", "period_end")
    received = cents(payload, "received_cents", "Valor recebido", required=True)
    received_on = day(payload.get("received_on") or today(), "Data do recebimento")
    not_paid = payload.get("not_paid_task_ids") or []
    if not isinstance(not_paid, list) or not all(isinstance(i, str) for i in not_paid):
        raise ValidationError("Tarefas não pagas: lista inválida")
    all_in_period = finished_in(deps.repo.list_tasks(owner, project.id), start, end)
    tasks = [t for t in all_in_period if not t.billed]
    if not tasks:
        raise ValidationError("Nenhuma tarefa em aberto neste período")
    open_ids = {t.id for t in tasks}
    unknown = set(not_paid) - open_ids
    if unknown:
        raise ValidationError("Tarefas não pagas: alguma não está em aberto neste período")
    payments = overlapping_payments(deps.repo.list_payments(owner, project.id), start, end)
    bonus_cents, _ = bonus(project, all_in_period)
    bonus_due = max(0, bonus_cents - sum(p.bonus_cents for p in payments))
    values = {t.id: task_value(t, project.rule_at(t.finished_at)) for t in tasks}
    paid_values = {i: v for i, v in values.items() if i not in not_paid}
    payment = Payment(new_id(), project.id, start, end, received_on, received,
                      sum(paid_values.values()) + bonus_due, bonus_due, paid_values,
                      {i: values[i] for i in not_paid}, text(payload, "notes", "Observações", max_length=2000))
    deps.repo.save_payment(owner, payment)
    deps.repo.save_tasks(owner, [replace(t, billing=NOT_PAID if t.id in not_paid else PAID, payment_id=payment.id)
                                 for t in tasks])
    return payment
