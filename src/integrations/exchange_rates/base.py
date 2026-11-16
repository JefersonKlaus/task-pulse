"""What the rest of the app knows about exchange rates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class ExchangeRateUnavailable(Exception):
    """The rate could not be fetched or understood."""


@dataclass(frozen=True)
class ExchangeRate:
    rate: Decimal  # reais per dollar
    quoted_at: str  # as reported by the source, e.g. "2026-11-16 10:00:00"


class ExchangeRateProvider(Protocol):
    """Anything that can tell the current dollar rate."""

    def usd_brl(self) -> ExchangeRate:
        """Return the rate, or raise ``ExchangeRateUnavailable``."""
