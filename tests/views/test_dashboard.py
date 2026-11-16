from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from src.integrations.exchange_rates import ExchangeRate, ExchangeRateUnavailable
from tests.factories import create_project, create_task

NOVEMBER = {"inicio": "2026-11-01", "fim": "2026-11-30"}
RATE = ExchangeRate(rate=Decimal("5.35"), quoted_at="2026-11-16 10:00:00")


@contextmanager
def rate_api(**kwargs):
    """Replace the dashboard's exchange-rate provider (no network).

    Yields the provider's ``usd_brl`` mock.
    """
    kwargs.setdefault("return_value", RATE)
    usd_brl = mock.Mock(**kwargs)
    with mock.patch(
        "src.views.dashboard.default_provider", return_value=mock.Mock(usd_brl=usd_brl)
    ):
        yield usd_brl


class DashboardViewTests(TestCase):
    url = reverse("tasks:dashboard")

    def setUp(self):
        project = create_project(name="Portal do Cliente")
        create_task(
            project,
            name="Login",
            status="DONE",
            minutes_spent=300,
            started_on=date(2026, 11, 3),
        )
        create_task(
            project,
            name="API",
            status="REJECTED",
            minutes_spent=90,
            started_on=date(2026, 11, 4),
        )

    def test_first_visit_shows_this_month_with_every_status(self):
        with mock.patch(
            "src.views.dashboard.timezone.localdate", return_value=date(2026, 11, 16)
        ):
            response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn('value="2026-11-01"', content)
        self.assertIn('value="2026-11-30"', content)
        self.assertEqual(content.count("checked"), 4)

    def test_shows_the_hours_and_the_tasks_with_their_status(self):
        response = self.client.get(self.url, NOVEMBER)
        self.assertContains(response, '<span class="value">6.50h</span>', html=True)
        self.assertContains(response, "Done: 1 tarefa · 5.00h")
        self.assertContains(
            response, '<span class="status">Rejeitado</span>', html=True
        )

    def test_values_in_dollars_and_reais(self):
        with rate_api():
            response = self.client.get(
                self.url,
                {**NOVEMBER, "valor_hora": "90", "valor_flat": "100", "bonus": "40"},
            )
        # Login 460 (4x90 + 100), API 135 (rejected: 1.5x90), bonus 40 -> 635
        self.assertContains(response, '<td class="number">US$ 460.00</td>', html=True)
        self.assertContains(
            response, '<span class="value">US$ 635.00</span>', html=True
        )
        self.assertContains(
            response, '<span class="value">R$ 3.397,25</span>', html=True
        )
        self.assertContains(response, "Cotação R$ 5,3500 em 2026-11-16 10:00:00")

    def test_only_the_checked_statuses_are_listed_and_calculated(self):
        response = self.client.get(self.url, {**NOVEMBER, "status": ["DONE"]})
        self.assertContains(response, '<span class="value">5.00h</span>', html=True)
        self.assertNotContains(response, "API")
        self.assertRegex(response.content.decode(), r'value="DONE"[^>]*checked')

    def test_without_an_hourly_rate_there_is_no_money_and_no_api_call(self):
        with rate_api() as api:
            response = self.client.get(self.url, NOVEMBER)
        api.assert_not_called()
        self.assertNotContains(response, "Total em dólar")

    def test_unavailable_rate_shows_a_warning(self):
        with rate_api(side_effect=ExchangeRateUnavailable("offline")):
            with self.assertLogs("src.services.dashboard", "WARNING"):
                response = self.client.get(self.url, {**NOVEMBER, "valor_hora": "90"})
        self.assertContains(
            response, '<span class="value">US$ 585.00</span>', html=True
        )
        self.assertContains(response, "Cotação do dólar indisponível no momento")

    def test_an_invalid_filter_shows_the_error_and_no_summary(self):
        response = self.client.get(
            self.url, {"inicio": "2026-11-30", "fim": "2026-11-01"}
        )
        self.assertContains(response, "A data final não pode ser anterior à inicial.")
        self.assertNotContains(response, "Horas trabalhadas")
