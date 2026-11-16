"""Build the dashboard: tasks of a period, their hours and value.

* A task belongs to the period of its start date ("Início").
* Only the selected statuses are listed and counted.
* With pricing, the dollar total is converted to reais at the current rate.
  If the rate is unavailable the report says so (and it is logged) instead
  of failing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..domain.money import usd_to_brl
from ..domain.period_summary import PeriodSummary, summarize
from ..domain.pricing import Pricing
from ..integrations.exchange_rates import (
    ExchangeRate,
    ExchangeRateProvider,
    ExchangeRateUnavailable,
)
from ..models import Task

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DashboardReport:
    summary: PeriodSummary
    exchange_rate: ExchangeRate | None = None
    total_brl: Decimal | None = None
    exchange_rate_unavailable: bool = False


def build_dashboard(
    *,
    start: date,
    end: date,
    statuses: list[str],
    pricing: Pricing | None,
    exchange_rates: ExchangeRateProvider,
) -> DashboardReport:
    """``exchange_rates`` is only asked for the rate when there is a dollar
    total to convert."""
    tasks = (
        Task.objects.started_between(start, end)
        .with_statuses(statuses)
        .select_related("project")
    )
    summary = summarize(tasks, pricing, statuses)
    if summary.total_usd is None:
        return DashboardReport(summary)
    try:
        rate = exchange_rates.usd_brl()
    except ExchangeRateUnavailable:
        logger.warning("USD/BRL exchange rate unavailable", exc_info=True)
        return DashboardReport(summary, exchange_rate_unavailable=True)
    return DashboardReport(
        summary, exchange_rate=rate, total_brl=usd_to_brl(summary.total_usd, rate.rate)
    )
