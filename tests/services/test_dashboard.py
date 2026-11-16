from datetime import date
from decimal import Decimal

from django.test import TestCase

from src.domain.pricing import Pricing
from src.integrations.exchange_rates import ExchangeRate, ExchangeRateUnavailable
from src.services.dashboard import build_dashboard
from tests.factories import create_project, create_task

ALL = ["DOING", "REVIEW", "DONE", "REJECTED"]
RATE = ExchangeRate(rate=Decimal("5.35"), quoted_at="2026-11-16 10:00:00")


class FakeExchangeRates:
    """An ExchangeRateProvider for tests: no network."""

    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def usd_brl(self):
        self.calls += 1
        if self.error:
            raise self.error
        return RATE


def build(statuses=ALL, pricing=None, exchange_rates=None):
    return build_dashboard(
        start=date(2026, 11, 1),
        end=date(2026, 11, 30),
        statuses=statuses,
        pricing=pricing,
        exchange_rates=exchange_rates or FakeExchangeRates(),
    )


def names(report):
    return sorted(line.task.name for line in report.summary.lines)


class BuildDashboardTasksTests(TestCase):
    """Which tasks are listed and calculated."""

    def setUp(self):
        project = create_project()
        for name, status, day in (
            ("Outubro", "DONE", date(2026, 10, 31)),
            ("Primeiro dia", "DONE", date(2026, 11, 1)),
            ("Recusada", "REJECTED", date(2026, 11, 15)),
            ("Último dia", "DOING", date(2026, 11, 30)),
            ("Dezembro", "DONE", date(2026, 12, 1)),
        ):
            create_task(
                project, name=name, status=status, started_on=day, minutes_spent=60
            )

    def test_tasks_started_in_the_period_including_both_ends(self):
        self.assertEqual(names(build()), ["Primeiro dia", "Recusada", "Último dia"])

    def test_only_the_selected_statuses_are_listed_and_calculated(self):
        report = build(statuses=["DONE", "REJECTED"], pricing=Pricing(Decimal("90")))
        self.assertEqual(names(report), ["Primeiro dia", "Recusada"])
        self.assertEqual(
            (report.summary.minutes, report.summary.total_usd), (120, Decimal("180.00"))
        )
        self.assertEqual(
            [total.label for total in report.summary.by_status], ["Done", "Rejeitado"]
        )


class BuildDashboardExchangeRateTests(TestCase):
    """The dollar total is converted to reais, when there is one."""

    def setUp(self):
        create_task(
            create_project(),
            status="DONE",
            minutes_spent=300,
            started_on=date(2026, 11, 3),
        )

    def test_without_pricing_the_rate_is_not_asked(self):
        rates = FakeExchangeRates()
        self.assertIsNone(build(exchange_rates=rates).total_brl)
        self.assertEqual(rates.calls, 0)

    def test_total_in_reais_includes_the_bonus(self):
        report = build(pricing=Pricing(Decimal("90"), Decimal("100"), Decimal("40")))
        # (460 + 40) x 5.35
        self.assertEqual(
            (report.exchange_rate, report.total_brl), (RATE, Decimal("2675.00"))
        )

    def test_unavailable_rate_keeps_the_dollar_total_and_is_logged(self):
        with self.assertLogs("src.services.dashboard", "WARNING") as logs:
            report = build(
                pricing=Pricing(Decimal("90")),
                exchange_rates=FakeExchangeRates(error=ExchangeRateUnavailable("x")),
            )
        self.assertEqual(
            (
                report.summary.total_usd,
                report.total_brl,
                report.exchange_rate_unavailable,
            ),
            (Decimal("450.00"), None, True),
        )
        self.assertIn("USD/BRL exchange rate unavailable", logs.output[0])
