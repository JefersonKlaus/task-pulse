import re
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from src.models import Payment
from tests.factories import create_payment, create_project, create_task

OCT_NOV = {"inicio": "2026-10-01", "fim": "2026-11-30", "agrupar": "mes"}


class StatisticsViewTests(TestCase):
    url = reverse("tasks:statistics")

    def test_first_visit_shows_the_last_twelve_months(self):
        with mock.patch(
            "src.views.statistics.timezone.localdate", return_value=date(2026, 11, 17)
        ):
            response = self.client.get(self.url)
        self.assertContains(response, 'value="2025-12-01"')
        self.assertContains(response, 'value="2026-11-30"')
        self.assertContains(response, "Nenhuma tarefa ou pagamento neste período.")

    def test_shows_the_totals_and_the_charts(self):
        project = create_project(name="Portal do Cliente")
        paid = create_task(
            project, status="DONE", minutes_spent=120, started_on=date(2026, 10, 5)
        )
        create_task(
            project, status="DOING", minutes_spent=30, started_on=date(2026, 11, 5)
        )
        payment = create_payment(paid, paid_usd=Decimal("200.00"))
        Payment.objects.filter(pk=payment.pk).update(
            created_at=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
        )
        response = self.client.get(self.url, OCT_NOV)
        for text in (
            '<span class="value">2.50h</span>',  # hours
            "0.50h não pagas",
            '<span class="value">2</span>',  # tasks
            "1 concluída",
            '<span class="value">US$ 200.00</span>',  # received
            '<span class="value">US$ 100.00</span>',  # per hour paid: 200 / 2h
            "Portal do Cliente",
            'title="out/26: Pagas 2.00h · Não pagas 0.00h · Total 2.00h"',
            'title="nov/26: Recebido US$ 200.00"',
        ):
            with self.subTest(text=text):
                self.assertContains(response, text, html=text.startswith("<"))

    def test_by_week(self):
        create_task(minutes_spent=60, started_on=date(2026, 11, 30))
        response = self.client.get(self.url, {**OCT_NOV, "agrupar": "semana"})
        self.assertContains(response, "Por semana de início das tarefas.")
        self.assertContains(response, 'title="30/11: Pagas 0.00h · Não pagas 1.00h')

    def test_bar_sizes_are_valid_css_in_portuguese(self):
        # Numbers in templates are localized ("50,00"); CSS needs "50.00".
        create_task(minutes_spent=60, started_on=date(2026, 10, 5))
        create_task(minutes_spent=30, started_on=date(2026, 11, 5))
        content = self.client.get(self.url, OCT_NOV).content.decode()
        sizes = re.findall(r'style="(?:height|bottom|width): ([^"]*)"', content)
        self.assertTrue(sizes)
        for size in sizes:
            with self.subTest(size=size):
                self.assertRegex(size, r"^\d+\.\d\d%$")

    def test_an_invalid_filter_shows_the_errors_and_no_charts(self):
        response = self.client.get(self.url, {**OCT_NOV, "fim": "2026-09-01"})
        self.assertContains(response, "A data final não pode ser anterior à inicial.")
        self.assertNotContains(response, 'class="charts"')
