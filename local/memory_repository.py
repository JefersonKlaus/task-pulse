"""In-memory repository: used in tests and to run without AWS. Never deployed (the Lambdas use DynamoDB)."""
from __future__ import annotations

import threading
from typing import Any, Optional

from pulse_core.domain.models import Company, Payment, Project, Task


class MemoryRepository:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()       # the local server answers several requests at once

    def _owner(self, owner: str) -> dict[str, Any]:
        with self._lock:
            return self._data.setdefault(owner, {"companies": {}, "projects": {}, "tasks": {}, "payments": {}})

    # companies
    def list_companies(self, owner: str) -> list[Company]:
        return list(self._owner(owner)["companies"].values())

    def get_company(self, owner: str, id: str) -> Optional[Company]:
        return self._owner(owner)["companies"].get(id)

    def save_company(self, owner: str, company: Company) -> None:
        self._owner(owner)["companies"][company.id] = company

    def delete_company(self, owner: str, id: str) -> None:
        self._owner(owner)["companies"].pop(id, None)

    # projects
    def list_projects(self, owner: str) -> list[Project]:
        return list(self._owner(owner)["projects"].values())

    def get_project(self, owner: str, id: str) -> Optional[Project]:
        return self._owner(owner)["projects"].get(id)

    def save_project(self, owner: str, project: Project) -> None:
        self._owner(owner)["projects"][project.id] = project

    def delete_project(self, owner: str, id: str) -> None:
        self._owner(owner)["projects"].pop(id, None)

    # tasks
    def list_tasks(self, owner: str, project_id: Optional[str] = None) -> list[Task]:
        return [t for t in list(self._owner(owner)["tasks"].values()) if project_id is None or t.project_id == project_id]

    def get_task(self, owner: str, project_id: str, id: str) -> Optional[Task]:
        return self._owner(owner)["tasks"].get((project_id, id))

    def save_tasks(self, owner: str, tasks: list[Task]) -> None:
        for t in tasks:
            self._owner(owner)["tasks"][(t.project_id, t.id)] = t

    def delete_tasks(self, owner: str, project_id: str, ids: list[str]) -> None:
        for id in ids:
            self._owner(owner)["tasks"].pop((project_id, id), None)

    # payments
    def list_payments(self, owner: str, project_id: Optional[str] = None) -> list[Payment]:
        return [p for p in list(self._owner(owner)["payments"].values())
                if project_id is None or p.project_id == project_id]

    def get_payment(self, owner: str, project_id: str, id: str) -> Optional[Payment]:
        return self._owner(owner)["payments"].get((project_id, id))

    def save_payment(self, owner: str, payment: Payment) -> None:
        self._owner(owner)["payments"][(payment.project_id, payment.id)] = payment

    def delete_payments(self, owner: str, project_id: str, ids: list[str]) -> None:
        for id in ids:
            self._owner(owner)["payments"].pop((project_id, id), None)
