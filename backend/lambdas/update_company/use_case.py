"""Use case (application layer): Renames one of the user's own companies or changes its notes. A
well-known company is the same for everyone and is not edited (it can only be removed from the list).
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any, Mapping

from pulse_core.application import check_unique_company_name, company_or_404
from pulse_core.domain.catalog import known_by_name
from pulse_core.domain.errors import Conflict, ValidationError
from pulse_core.domain.models import Company
from pulse_core.ports import Dependencies


def update_company(deps: Dependencies, owner: str, id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if company_or_404(deps, owner, id).known:
        raise Conflict("Empresa padrão: não pode ser editada")
    company = Company.from_input(payload, id)
    if known_by_name(company.name):
        raise ValidationError("Este nome é de uma empresa padrão: adicione-a em Empresas conhecidas")
    check_unique_company_name(deps, owner, company)
    deps.repo.save_company(owner, company)
    return company.to_dict()
