"""Build the billing page: tasks of a period, their hours and value.

* A task belongs to the period of its start date ("Início").
* With a company (``provider``), only its projects' tasks count.
* Only the selected statuses are listed and counted.
* Tasks already paid are listed and counted only with ``include_paid``.
* With pricing, the dollar total is converted to reais at the current rate.
  If the rate is unavailable the report says so (and it is logged) instead
  of failing.
* With pricing, the report also has what is still to pay: the same totals
  for the listed tasks that are not paid yet (see ``services.payments``).
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
from ..models import Provider, Task

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BillingReport:
    summary: PeriodSummary
    exchange_rate: ExchangeRate | None = None
    total_brl: Decimal | None = None
    exchange_rate_unavailable: bool = False
    # The unpaid listed tasks, priced; None without pricing or unpaid tasks.
    to_pay: PeriodSummary | None = None
    to_pay_brl: Decimal | None = None  # None without an exchange rate

    @property
    def paid_tasks(self):
        """How many listed tasks were already paid."""
        return sum(1 for line in self.summary.lines if line.task.payment_id)

    @property
    def tasks_without_provider(self):
        """How many listed unpaid tasks can't be paid: their project has no
        company (payments are made by a company)."""
        return sum(
            1
            for line in self.summary.lines
            if not line.task.payment_id and line.task.project.provider_id is None
        )


def build_billing(
    *,
    start: date,
    end: date,
    statuses: list[str],
    pricing: Pricing | None,
    exchange_rates: ExchangeRateProvider,
    include_paid: bool = True,
    provider: Provider | None = None,
) -> BillingReport:
    """``exchange_rates`` is only asked for the rate when there is a dollar
    total to convert."""
    tasks = (
        Task.objects.started_between(start, end)
        .with_statuses(statuses)
        .of_provider(provider)
    )
    if not include_paid:
        tasks = tasks.unpaid()
    tasks = list(tasks.select_related("project"))
    summary = summarize(tasks, pricing, statuses)
    if summary.total_usd is None:
        return BillingReport(summary)
    unpaid = [task for task in tasks if task.payment_id is None]
    to_pay = summarize(unpaid, pricing, statuses) if unpaid else None
    try:
        rate = exchange_rates.usd_brl()
    except ExchangeRateUnavailable:
        logger.warning("USD/BRL exchange rate unavailable", exc_info=True)
        return BillingReport(summary, exchange_rate_unavailable=True, to_pay=to_pay)
    return BillingReport(
        summary,
        exchange_rate=rate,
        total_brl=usd_to_brl(summary.total_usd, rate.rate),
        to_pay=to_pay,
        to_pay_brl=usd_to_brl(to_pay.total_usd, rate.rate) if to_pay else None,
    )
