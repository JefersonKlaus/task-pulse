"""Entities and their validation: Company, Project (with its pricing Rules), Task and Payment.

Conventions:
- Money is always integer cents (`hourly_cents`, `received_cents`...), never a float.
- A moment is "YYYY-MM-DDTHH:MM" (Brasília time, minute precision); a day is "YYYY-MM-DD". Both sort
  as text, so comparing the strings compares the moments.
- Time worked is whole minutes, so repeated additions stay exact.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any, Mapping, Optional

from .errors import ValidationError

ITEM_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
CURRENCIES = ("BRL", "USD", "EUR")
RULE_KINDS = ("hourly", "fixed")        # paid by the hour, or a fixed amount per task

DOING, DONE, APPROVED, REJECTED = "DOING", "DONE", "APPROVED", "REJECTED"
STATUSES = (DOING, DONE, APPROVED, REJECTED)
FINISHED = (DONE, APPROVED, REJECTED)   # concluded: they have a finish moment and can be billed

PAID, NOT_PAID = "paid", "not_paid"     # Task.billing after a payment; "" = not billed yet

MAX_MINUTES = 100_000 * 60              # no task takes more than this
MAX_CENTS = 10**12


def new_id() -> str:
    return uuid.uuid4().hex


# ------------------------------------------------------------------ input helpers
def text(payload: Mapping[str, Any], key: str, label: str, *, max_length: int = 200,
         required: bool = False) -> str:
    value = payload.get(key)
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"{label}: texto inválido")
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{label}: obrigatório")
    if len(value) > max_length:
        raise ValidationError(f"{label}: no máximo {max_length} caracteres")
    return value


def cents(payload: Mapping[str, Any], key: str, label: str, *, required: bool = False,
          allow_zero: bool = True) -> Optional[int]:
    value = payload.get(key)
    if value is None or value == "":
        if required:
            raise ValidationError(f"{label}: obrigatório")
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > MAX_CENTS:
        raise ValidationError(f"{label}: valor inválido (centavos, inteiro)")
    if value == 0 and not allow_zero:
        raise ValidationError(f"{label}: deve ser maior que zero")
    return value


def minutes(payload: Mapping[str, Any], key: str, label: str = "Tempo") -> int:
    value = payload.get(key, 0)
    if value is None or value == "":
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_MINUTES:
        raise ValidationError(f"{label}: minutos inválidos")
    return value


def day(value: Any, label: str, *, required: bool = True) -> Optional[str]:
    if value in (None, ""):
        if required:
            raise ValidationError(f"{label}: obrigatório")
        return None
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValidationError(f"{label}: data inválida (AAAA-MM-DD)") from None


def moment(value: Any, label: str, *, required: bool = True) -> Optional[str]:
    """"2026-11-26T14:30" (seconds are dropped). A day alone is that day at 00:00."""
    if value in (None, ""):
        if required:
            raise ValidationError(f"{label}: obrigatório")
        return None
    raw = str(value)
    try:
        if len(raw) == 10:
            return date.fromisoformat(raw).isoformat() + "T00:00"
        return datetime.fromisoformat(raw).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        raise ValidationError(f"{label}: data e hora inválidas (AAAA-MM-DDTHH:MM)") from None


def flag(payload: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ValidationError(f"{key}: deve ser true ou false")
    return value


# ------------------------------------------------------------------ company
@dataclass(frozen=True)
class Company:
    """A company the work is done for. Its projects, tasks and payments are kept apart from the others'."""
    id: str
    name: str
    notes: str = ""

    @classmethod
    def from_input(cls, payload: Mapping[str, Any], id: Optional[str] = None) -> "Company":
        return cls(id or new_id(), text(payload, "name", "Nome", max_length=100, required=True),
                   text(payload, "notes", "Observações", max_length=2000))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "notes": self.notes}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Company":
        return cls(d["id"], d["name"], d.get("notes", ""))


# ------------------------------------------------------------------ pricing rules
@dataclass(frozen=True)
class BonusTier:
    """`bonus_cents` when at least `min_tasks` approved tasks were delivered in the billed period."""
    min_tasks: int
    bonus_cents: int

    def to_dict(self) -> dict[str, Any]:
        return {"min_tasks": self.min_tasks, "bonus_cents": self.bonus_cents}


@dataclass(frozen=True)
class Rule:
    """How a project pays, from `starts_at` until `ends_at` (excluded; None = until another rule starts).
    A task is priced by the rule in force at the moment it was finished, so a rule that changes today
    never changes what a task finished yesterday is worth.

    - kind "hourly": every minute at `hourly_cents`/h; with `flat_cents`, an APPROVED task has its last
      hour (or all of it, if under an hour) paid at `flat_cents`/h instead.
    - kind "fixed": `fixed_cents` per task, whatever the time.
    - `paid_only_if_approved`: only APPROVED tasks are paid (DONE and REJECTED are worth 0).
      Without it, DONE and APPROVED are paid and only REJECTED is worth 0.
    - `bonus_tiers`: extra money once per billed period, by how many tasks were approved in it.
    """
    id: str
    starts_at: str
    ends_at: Optional[str]
    kind: str
    hourly_cents: int = 0
    flat_cents: Optional[int] = None
    fixed_cents: int = 0
    paid_only_if_approved: bool = False
    bonus_tiers: tuple[BonusTier, ...] = ()

    def covers(self, at: str) -> bool:
        return self.starts_at <= at and (self.ends_at is None or at < self.ends_at)

    def overlaps(self, other: "Rule") -> bool:
        return ((other.ends_at is None or self.starts_at < other.ends_at)
                and (self.ends_at is None or other.starts_at < self.ends_at))

    def same_pricing(self, other: "Rule") -> bool:
        return (self.kind, self.hourly_cents, self.flat_cents, self.fixed_cents, self.paid_only_if_approved,
                self.bonus_tiers, self.starts_at) == (other.kind, other.hourly_cents, other.flat_cents,
                                                       other.fixed_cents, other.paid_only_if_approved,
                                                       other.bonus_tiers, other.starts_at)

    @classmethod
    def from_input(cls, payload: Mapping[str, Any], id: Optional[str] = None) -> "Rule":
        kind = payload.get("kind")
        if kind not in RULE_KINDS:
            raise ValidationError("Tipo de valor: escolha valor hora ou valor fixo")
        starts_at = moment(payload.get("starts_at"), "Início da regra")
        ends_at = moment(payload.get("ends_at"), "Fim da regra", required=False)
        if ends_at is not None and ends_at <= starts_at:
            raise ValidationError("Fim da regra deve ser depois do início")
        hourly = flat = None
        fixed = 0
        if kind == "hourly":
            hourly = cents(payload, "hourly_cents", "Valor hora", required=True, allow_zero=False)
            flat = cents(payload, "flat_cents", "Valor flat", allow_zero=False)
        else:
            fixed = cents(payload, "fixed_cents", "Valor fixo", required=True, allow_zero=False)
        tiers_input = payload.get("bonus_tiers") or []
        if not isinstance(tiers_input, list) or len(tiers_input) > 20:
            raise ValidationError("Bônus: lista inválida")
        tiers: list[BonusTier] = []
        for item in tiers_input:
            if not isinstance(item, Mapping):
                raise ValidationError("Bônus: item inválido")
            count = item.get("min_tasks")
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 10_000:
                raise ValidationError("Bônus: número de tarefas inválido")
            tiers.append(BonusTier(count, cents(item, "bonus_cents", "Bônus", required=True, allow_zero=False)))
        if len({t.min_tasks for t in tiers}) != len(tiers):
            raise ValidationError("Bônus: cada faixa precisa de um número de tarefas diferente")
        return cls(id or new_id(), starts_at, ends_at, kind, hourly or 0, flat, fixed,
                   flag(payload, "paid_only_if_approved"), tuple(sorted(tiers, key=lambda t: t.min_tasks)))

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "starts_at": self.starts_at, "ends_at": self.ends_at, "kind": self.kind,
                "hourly_cents": self.hourly_cents, "flat_cents": self.flat_cents, "fixed_cents": self.fixed_cents,
                "paid_only_if_approved": self.paid_only_if_approved,
                "bonus_tiers": [t.to_dict() for t in self.bonus_tiers]}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Rule":
        return cls(d["id"], d["starts_at"], d.get("ends_at"), d["kind"], d.get("hourly_cents", 0),
                   d.get("flat_cents"), d.get("fixed_cents", 0), d.get("paid_only_if_approved", False),
                   tuple(BonusTier(t["min_tasks"], t["bonus_cents"]) for t in d.get("bonus_tiers", [])))


# ------------------------------------------------------------------ project
@dataclass(frozen=True)
class Project:
    id: str
    company_id: str
    name: str
    currency: str = "BRL"
    deadline: Optional[str] = None          # the day the project ends (informative)
    description: str = ""
    rules: tuple[Rule, ...] = ()

    @classmethod
    def from_input(cls, payload: Mapping[str, Any], id: Optional[str] = None,
                   rules: tuple[Rule, ...] = ()) -> "Project":
        company_id = payload.get("company_id")
        if not isinstance(company_id, str) or not ITEM_ID_RE.match(company_id):
            raise ValidationError("Empresa: obrigatória")
        currency = payload.get("currency") or "BRL"
        if currency not in CURRENCIES:
            raise ValidationError("Moeda inválida")
        return cls(id or new_id(), company_id, text(payload, "name", "Nome", max_length=120, required=True),
                   currency, day(payload.get("deadline"), "Deadline", required=False),
                   text(payload, "description", "Descrição", max_length=4000), rules)

    def rule_at(self, at: Optional[str]) -> Optional[Rule]:
        if not at:
            return None
        return next((r for r in self.rules if r.covers(at)), None)

    def current_rule(self, now: str) -> Optional[Rule]:
        return self.rule_at(now)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "company_id": self.company_id, "name": self.name, "currency": self.currency,
                "deadline": self.deadline, "description": self.description,
                "rules": [r.to_dict() for r in sorted(self.rules, key=lambda r: r.starts_at)]}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Project":
        return cls(d["id"], d["company_id"], d["name"], d.get("currency", "BRL"), d.get("deadline"),
                   d.get("description", ""), tuple(Rule.from_dict(r) for r in d.get("rules", [])))


# ------------------------------------------------------------------ task
@dataclass(frozen=True)
class TimeEntry:
    at: str
    minutes: int

    def to_dict(self) -> dict[str, Any]:
        return {"at": self.at, "minutes": self.minutes}


@dataclass(frozen=True)
class Task:
    id: str
    project_id: str
    name: str
    started_at: str
    status: str = DOING
    finished_at: Optional[str] = None
    minutes: int = 0
    external_id: str = ""
    repository: str = ""
    description: str = ""
    time_log: tuple[TimeEntry, ...] = ()
    billing: str = ""                       # "" | PAID | NOT_PAID
    payment_id: Optional[str] = None

    @property
    def finished(self) -> bool:
        return self.status in FINISHED

    @property
    def billed(self) -> bool:
        return bool(self.payment_id)

    @classmethod
    def from_input(cls, payload: Mapping[str, Any], project_id: str, now: str) -> "Task":
        status = payload.get("status") or DOING
        if status not in STATUSES:
            raise ValidationError("Status inválido")
        started_at = moment(payload.get("started_at"), "Início", required=False) or now
        spent = minutes(payload, "minutes")
        finished_at = None
        if status in FINISHED:
            finished_at = moment(payload.get("finished_at"), "Término", required=False)
            if finished_at is None:
                raise ValidationError("Tarefa concluída: informe quando terminou")
            if spent <= 0:
                raise ValidationError("Tarefa concluída: informe o tempo trabalhado")
            if finished_at < started_at:
                raise ValidationError("Término não pode ser antes do início")
        log = (TimeEntry(finished_at or now, spent),) if spent else ()
        return cls(new_id(), project_id, text(payload, "name", "Nome", max_length=200, required=True),
                   started_at, status, finished_at, spent,
                   text(payload, "external_id", "ID externo", max_length=100),
                   text(payload, "repository", "Repositório", max_length=300),
                   text(payload, "description", "Descrição", max_length=8000), log)

    def edited(self, payload: Mapping[str, Any], now: str) -> "Task":
        """The task with the fields in `payload` changed. A billed task only changes its texts: what was
        paid for it stays as it was."""
        changes: dict[str, Any] = {}
        for key, label, size in (("name", "Nome", 200), ("external_id", "ID externo", 100),
                                 ("repository", "Repositório", 300), ("description", "Descrição", 8000)):
            if key in payload:
                changes[key] = text(payload, key, label, max_length=size, required=key == "name")
        pricing_keys = {"status", "started_at", "finished_at", "minutes"} & set(payload)
        if pricing_keys and self.billed:
            if any(payload[k] != getattr(self, k) for k in pricing_keys):
                raise ValidationError("Tarefa já faturada: só nome, ID, repositório e descrição podem mudar")
            pricing_keys = set()
        status = payload.get("status", self.status)
        if status not in STATUSES:
            raise ValidationError("Status inválido")
        started_at = moment(payload["started_at"], "Início") if "started_at" in payload else self.started_at
        spent = minutes(payload, "minutes") if "minutes" in payload else self.minutes
        if "finished_at" in payload:
            finished_at = moment(payload["finished_at"], "Término", required=False)
        else:
            finished_at = self.finished_at
        if status == DOING:
            finished_at = None
        elif finished_at is None:
            finished_at = now                       # concluded now
        if finished_at is not None and finished_at < started_at:
            raise ValidationError("Término não pode ser antes do início")
        if status in FINISHED and spent <= 0:
            raise ValidationError("Tarefa concluída: informe o tempo trabalhado")
        log = self.time_log
        if spent != self.minutes:
            log = log + (TimeEntry(now, spent - self.minutes),)
        if pricing_keys:
            changes.update(status=status, started_at=started_at, finished_at=finished_at, minutes=spent,
                           time_log=log)
        return replace(self, **changes)

    def with_time(self, spent: int, now: str, finish: bool = False,
                  finished_at: Optional[str] = None) -> "Task":
        if self.billed:
            raise ValidationError("Tarefa já faturada: o tempo não muda mais")
        if spent < 0 or (spent == 0 and not finish):
            raise ValidationError("Tempo: informe quantos minutos trabalhou")
        total = self.minutes + spent
        if total > MAX_MINUTES:
            raise ValidationError("Tempo: total grande demais")
        task = replace(self, minutes=total,
                       time_log=self.time_log + ((TimeEntry(now, spent),) if spent else ()))
        if finish:
            if total <= 0:
                raise ValidationError("Para concluir, informe o tempo trabalhado")
            end = finished_at or now
            if end < self.started_at:
                raise ValidationError("Término não pode ser antes do início")
            task = replace(task, status=DONE if self.status == DOING else self.status, finished_at=end)
        return task

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "project_id": self.project_id, "name": self.name, "started_at": self.started_at,
                "status": self.status, "finished_at": self.finished_at, "minutes": self.minutes,
                "external_id": self.external_id, "repository": self.repository, "description": self.description,
                "time_log": [e.to_dict() for e in self.time_log], "billing": self.billing,
                "payment_id": self.payment_id}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Task":
        return cls(d["id"], d["project_id"], d["name"], d["started_at"], d.get("status", DOING),
                   d.get("finished_at"), d.get("minutes", 0), d.get("external_id", ""), d.get("repository", ""),
                   d.get("description", ""), tuple(TimeEntry(e["at"], e["minutes"]) for e in d.get("time_log", [])),
                   d.get("billing", ""), d.get("payment_id"))


# ------------------------------------------------------------------ payment
@dataclass(frozen=True)
class Payment:
    """What was received for a project's tasks of a period. `task_values` freezes what each paid task
    was worth when the payment was registered; `not_paid_values`, the ones the company did not pay."""
    id: str
    project_id: str
    period_start: str
    period_end: str
    received_on: str
    received_cents: int
    expected_cents: int
    bonus_cents: int = 0
    task_values: dict[str, int] = field(default_factory=dict)
    not_paid_values: dict[str, int] = field(default_factory=dict)   # what each task not paid was worth
    notes: str = ""

    @property
    def not_paid_cents(self) -> int:
        return sum(self.not_paid_values.values())

    @property
    def difference_cents(self) -> int:
        return self.received_cents - self.expected_cents

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "project_id": self.project_id, "period_start": self.period_start,
                "period_end": self.period_end, "received_on": self.received_on,
                "received_cents": self.received_cents, "expected_cents": self.expected_cents,
                "bonus_cents": self.bonus_cents, "task_values": dict(self.task_values),
                "not_paid_values": dict(self.not_paid_values), "notes": self.notes}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Payment":
        return cls(d["id"], d["project_id"], d["period_start"], d["period_end"], d["received_on"],
                   d["received_cents"], d["expected_cents"], d.get("bonus_cents", 0), dict(d.get("task_values", {})),
                   dict(d.get("not_paid_values", {})), d.get("notes", ""))
