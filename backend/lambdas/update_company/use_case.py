"""Use case (application layer): Renames a company or changes its notes.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import check_unique_company_name, company_or_404
from pulse_core.domain.models import Company
from pulse_core.ports import Dependencies


def update_company(deps: Dependencies, owner: str, id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    company_or_404(deps, owner, id)
    company = Company.from_input(payload, id)
    check_unique_company_name(deps, owner, company)
    deps.repo.save_company(owner, company)
    return company.to_dict()
