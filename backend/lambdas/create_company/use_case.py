"""Use case (application layer): Adds a company the work is done for: a well-known one (`known_id`, or a
name that is one of them: the same company for everyone, domain/catalog.py) or one of the user's own.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import MAX_COMPANIES, check_unique_company_name
from pulse_core.domain.catalog import known_by_id, known_by_name
from pulse_core.domain.errors import ValidationError
from pulse_core.domain.models import Company
from pulse_core.ports import Dependencies


def create_company(deps: Dependencies, owner: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("known_id") is not None:
        company = known_by_id(payload.get("known_id") if isinstance(payload.get("known_id"), str) else None)
        if company is None:
            raise ValidationError("Empresa padrão não encontrada")
    else:
        typed = Company.from_input(payload)
        company = known_by_name(typed.name) or typed
    if len(deps.repo.list_companies(owner)) >= MAX_COMPANIES:
        raise ValidationError(f"Limite de {MAX_COMPANIES} empresas")
    if company.known and deps.repo.get_company(owner, company.id):     # chosen already
        raise ValidationError("Já existe uma empresa com este nome")
    check_unique_company_name(deps, owner, company)
    deps.repo.save_company(owner, company)
    return company.to_dict()
