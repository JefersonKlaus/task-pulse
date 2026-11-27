"""The well-known companies of AI training work (data annotation, evaluation, writing and review of model
answers). They are the same for everyone: a fixed id, name and notes, kept here and never edited by a
user. Choosing one only records the choice in the user's data (a Company with `known` and this id), so
every project of, say, Alignerr points to the same company "alignerr", whoever registered it: that is what
reports across people group by. The lesser-known companies are registered by each person, as before.

Notes are in Portuguese, the language the backend writes in; the site translates them (frontend
known-companies.ts). To add a company, add a line: its id must never change once someone chose it."""
from __future__ import annotations

from typing import Optional

from .models import Company

KNOWN_COMPANIES: tuple[Company, ...] = tuple(Company(id, name, notes, known=True) for id, name, notes in (
    ("alignerr", "Alignerr", "Plataforma da Labelbox."),
    ("appen", "Appen", ""),
    ("dataannotation", "DataAnnotation", ""),
    ("handshake-ai", "Handshake AI", ""),
    ("invisible-technologies", "Invisible Technologies", ""),
    ("mercor", "Mercor", ""),
    ("micro1", "micro1", ""),
    ("mindrift", "Mindrift", "Plataforma da Toloka."),
    ("outlier", "Outlier", "Plataforma da Scale AI."),
    ("prolific", "Prolific", ""),
    ("telus-digital", "TELUS Digital", ""),
    ("toloka", "Toloka", ""),
    ("turing", "Turing", ""),
))
_BY_ID = {c.id: c for c in KNOWN_COMPANIES}
_BY_NAME = {c.name.casefold(): c for c in KNOWN_COMPANIES}


def known_by_id(id: Optional[str]) -> Optional[Company]:
    return _BY_ID.get(id or "")


def known_by_name(name: str) -> Optional[Company]:
    """The well-known company with this name, ignoring case and spaces around it."""
    return _BY_NAME.get(name.strip().casefold())


def resolve(company: Company) -> Company:
    """What the user's record of a company shows: for a well-known one, the catalog's id, name and notes
    (the same for everyone, even if the catalog changed after it was chosen)."""
    return _BY_ID.get(company.id, company) if company.known else company
