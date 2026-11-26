"""Use case (application layer): Registers a company the work is done for.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import MAX_COMPANIES, check_unique_company_name
from pulse_core.domain.errors import ValidationError
from pulse_core.domain.models import Company
from pulse_core.ports import Dependencies


def create_company(deps: Dependencies, owner: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    company = Company.from_input(payload)
    if len(deps.repo.list_companies(owner)) >= MAX_COMPANIES:
        raise ValidationError(f"Limite de {MAX_COMPANIES} empresas")
    check_unique_company_name(deps, owner, company)
    deps.repo.save_company(owner, company)
    return company.to_dict()
