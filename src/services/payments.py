"""Payments: register the billing page's unpaid tasks as paid, list and export them.

* A payment is made by one company (``provider``): it covers the tasks of
  that company's projects that the billing page lists for a filter and that
  are not paid yet; tasks paid before are left out (a task is never paid
  twice). Without a company, nothing is paid.
* The estimate is calculated again here, from the filter, exactly as the
  billing page does; values sent by the browser are never trusted.
* ``task_ids`` are the tasks the user saw when confirming. If the list
  changed since then (a task was added, removed or paid meanwhile), nothing
  is saved and ``PaymentError`` asks the user to check again. The stored
  estimate is always the one calculated at saving time.
* The payment and the tasks' link to it are saved in one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.paginator import Page, Paginator
from django.db import transaction
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from ..domain.pricing import Pricing
from ..integrations.exchange_rates import ExchangeRateProvider
from ..integrations.payments_csv import write_payments_csv
from ..models import Payment, Provider, Task
from .billing import build_billing

LIST_CHANGED = _(
    "A lista de tarefas a pagar mudou desde que o pagamento foi aberto. "
    "Confira os valores e tente de novo."
)
NOTHING_TO_PAY = _("Não há tarefas a pagar com este filtro.")
NO_PROVIDER = _("Escolha a empresa que está pagando.")


class PaymentError(Exception):
    """The payment cannot be registered; the message explains why."""


def register_payment(
    *,
    start: date,
    end: date,
    statuses: list[str],
    pricing: Pricing | None,
    exchange_rates: ExchangeRateProvider,
    task_ids: list[int],
    paid_usd: Decimal,
    paid_brl: Decimal,
    provider: Provider | None,
) -> Payment:
    """Create the ``Payment`` and mark its tasks as paid."""
    if provider is None:
        raise PaymentError(NO_PROVIDER)
    report = build_billing(
        start=start,
        end=end,
        statuses=statuses,
        pricing=pricing,
        exchange_rates=exchange_rates,
        provider=provider,
    )
    if report.to_pay is None:
        raise PaymentError(NOTHING_TO_PAY)
    to_pay_ids = {line.task.pk for line in report.to_pay.lines}
    if to_pay_ids != set(task_ids):
        raise PaymentError(LIST_CHANGED)

    with transaction.atomic():
        payment = Payment.objects.create(
            period_start=start,
            period_end=end,
            estimated_usd=report.to_pay.total_usd,
            estimated_brl=report.to_pay_brl,
            paid_usd=paid_usd,
            paid_brl=paid_brl,
        )
        # Only unpaid tasks are linked: if another payment took one of them
        # meanwhile, the counts differ and everything is rolled back.
        linked = Task.objects.filter(pk__in=to_pay_ids).unpaid().update(payment=payment)
        if linked != len(to_pay_ids):
            raise PaymentError(LIST_CHANGED)
    return payment


PAGE_SIZE = 10


@dataclass(frozen=True)
class PaymentTotals:
    """The sums of a group of payments."""

    count: int
    estimated_usd: Decimal
    paid_usd: Decimal
    paid_brl: Decimal
    # None when a payment has no estimate in reais (rate was unavailable).
    estimated_brl: Decimal | None

    @classmethod
    def of(cls, payments):
        payments = list(payments)
        estimates_brl = [payment.estimated_brl for payment in payments]
        return cls(
            count=len(payments),
            estimated_usd=sum((p.estimated_usd for p in payments), Decimal("0.00")),
            paid_usd=sum((p.paid_usd for p in payments), Decimal("0.00")),
            paid_brl=sum((p.paid_brl for p in payments), Decimal("0.00")),
            estimated_brl=(
                None if None in estimates_brl else sum(estimates_brl, Decimal("0.00"))
            ),
        )

    @property
    def difference_usd(self):
        return self.paid_usd - self.estimated_usd

    @property
    def difference_brl(self):
        if self.estimated_brl is None:
            return None
        return self.paid_brl - self.estimated_brl


@dataclass(frozen=True)
class PaymentHistory:
    # This page's payments, newest first, each with its tasks, task_count
    # and minutes.
    page: Page
    totals: PaymentTotals  # of every payment
    page_totals: PaymentTotals  # of the payments on this page

    @property
    def payments(self):
        return list(self.page)


def payment_history(
    page_number=1, per_page=PAGE_SIZE, provider=None
) -> PaymentHistory:
    """One page of payments, with their tasks, and the totals.

    With a company (``provider``), only its payments (see
    ``PaymentQuerySet.of_provider``). An invalid or out-of-range
    ``page_number`` gives the first or the last page, so an old link never
    fails.
    """
    payments = _newest_first_with_task_totals(provider).prefetch_related(
        Prefetch("tasks", queryset=Task.objects.select_related("project"))
    )
    page = Paginator(payments, per_page).get_page(page_number)
    every_payment = Payment.objects.of_provider(provider).only(
        "estimated_usd", "estimated_brl", "paid_usd", "paid_brl"
    )
    return PaymentHistory(
        page=page,
        totals=PaymentTotals.of(every_payment),
        page_totals=PaymentTotals.of(page),
    )


def payments_csv(provider=None) -> str:
    """Every payment (of ``provider``, if given), newest first, as the CSV
    text of the report."""
    return write_payments_csv(_newest_first_with_task_totals(provider))


def _newest_first_with_task_totals(provider=None):
    # Explicit: Django ignores Meta.ordering in queries with aggregates.
    return (
        Payment.objects.of_provider(provider)
        .with_task_totals()
        .order_by("-created_at", "-pk")
    )
