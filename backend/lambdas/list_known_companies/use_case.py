"""Use case (application layer): The well-known companies (domain/catalog.py): id, name and notes, the
same for everyone. The site offers the ones the user hasn't chosen yet.
Depends only on the core's domain and ports, never on AWS."""
from __future__ import annotations

from typing import Any

from pulse_core.domain.catalog import KNOWN_COMPANIES
from pulse_core.ports import Dependencies


def list_known_companies(deps: Dependencies, owner: str) -> list[dict[str, Any]]:
    return [c.to_dict() for c in KNOWN_COMPANIES]
