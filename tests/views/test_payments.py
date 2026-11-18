from datetime import date
from decimal import Decimal
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tests.factories import create_payment, create_project, create_task


class PaymentListViewTests(TestCase):
    url = reverse("tasks:payment_list")

    def test_lists_each_payment_with_its_values_and_tasks(self):
        task = create_task(
            create_project(name="Portal do Cliente"),
            name="Tela de login",
            external_id="TP-1",
            status="DONE",
            minutes_spent=300,
        )
        create_payment(
            task,
            period_start=date(2026, 11, 1),
            period_end=date(2026, 11, 30),
            estimated_usd=Decimal("460.00"),
            estimated_brl=Decimal("2461.00"),
            paid_usd=Decimal("450.00"),
            paid_brl=Decimal("2400.00"),
        )
        response = self.client.get(self.url)
        for text in (
            '<span class="nowrap">01/11/2026</span> a <span class="nowrap">30/11/2026</span>',
            "Registrado em",
            '<td class="number">1</td>',  # tasks
            '<td class="number">5.00h</td>',
            'US$ 460.00<span class="muted">R$ 2.461,00</span>',
            'US$ 450.00<span class="muted">R$ 2.400,00</span>',
            "#TP-1 Tela de login",
            "Portal do Cliente · Done · 5.00h",
            f'href="{reverse("tasks:task_update", args=[task.pk])}"',
        ):
            with self.subTest(text=text):
                self.assertContains(response, text)
        # Less than estimated: in red, in the payment's row and in the total.
        self.assertContains(
            response,
            '<td class="number negative">US$ -10.00<span class="muted">R$ -61,00</span>',
            count=2,
        )

    def test_payment_without_an_estimate_in_reais(self):
        create_payment(estimated_brl=None)
        response = self.client.get(self.url)
        self.assertContains(response, 'US$ 100.00<span class="muted">—</span>')
        self.assertContains(response, "Estimado —")

    def test_one_page_has_no_page_links(self):
        create_payment()
        response = self.client.get(self.url)
        self.assertNotContains(response, 'class="pagination"')
        self.assertContains(response, '<td colspan="3">Total</td>', html=True)

    def test_empty_list_points_to_billing(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Nenhum pagamento registrado.")
        self.assertContains(response, f'href="{reverse("tasks:billing")}"')
        self.assertNotContains(response, "<table")
        self.assertNotContains(response, reverse("tasks:payment_export"))

    def test_links_to_the_export(self):
        create_payment()
        self.assertContains(
            self.client.get(self.url), f'href="{reverse("tasks:payment_export")}"'
        )


class PaymentListPaginationTests(TestCase):
    url = reverse("tasks:payment_list")

    def setUp(self):
        # Payment n (1..12) was paid US$ n; the 12th is the newest.
        for n in range(1, 13):
            create_payment(paid_usd=Decimal(n), estimated_usd=Decimal(n))

    def page(self, number=None):
        params = {} if number is None else {"pagina": number}
        return self.client.get(self.url, params)

    def rows(self, response):
        return response.content.decode().count('<tr class="payment">')

    def test_first_page_shows_the_10_newest_and_links_to_the_next(self):
        response = self.page()
        self.assertEqual(self.rows(response), 10)
        self.assertContains(response, "Mostrando 1–10 de 12 pagamentos.")
        self.assertContains(
            response, '<span class="current" aria-current="page">1</span>', html=True
        )
        self.assertContains(
            response, '<a href="?pagina=2" rel="next">Próxima ›</a>', html=True
        )
        self.assertContains(
            response, '<span class="disabled">‹ Anterior</span>', html=True
        )

    def test_last_page_shows_the_rest_and_links_back(self):
        response = self.page(2)
        self.assertEqual(self.rows(response), 2)
        self.assertContains(response, "Mostrando 11–12 de 12 pagamentos.")
        self.assertContains(
            response, '<a href="?pagina=1" rel="prev">‹ Anterior</a>', html=True
        )
        self.assertContains(
            response, '<span class="disabled">Próxima ›</span>', html=True
        )

    def test_cards_total_every_payment_and_the_footer_only_this_page(self):
        response = self.page(2)  # payments 2 and 1
        self.assertContains(response, '<span class="value">12</span>', html=True)
        # 1 + 2 + ... + 12 = 78
        self.assertContains(response, '<span class="value">US$ 78.00</span>', html=True)
        self.assertContains(response, '<td colspan="3">Total desta página</td>')
        # Page 2 is payments 2 and 1: US$ 3, and R$ 530 each.
        self.assertContains(
            response, '<td class="number">US$ 3.00<span class="muted">R$ 1.060,00'
        )

    def test_a_page_out_of_range_shows_the_last_one(self):
        self.assertEqual(self.rows(self.page(99)), 2)

    def test_the_number_of_queries_does_not_grow_with_the_payments(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.page(2)
            return len(captured)

        few = queries()
        project = create_project()
        for _ in range(30):  # more payments, each with tasks
            create_payment(create_task(project), create_task(project))
        self.assertEqual(queries(), few)


class PaymentExportViewTests(TestCase):
    url = reverse("tasks:payment_export")

    @mock.patch(
        "src.views.payments.timezone.localdate", return_value=date(2026, 11, 20)
    )
    def test_downloads_every_payment_as_a_dated_csv_file(self, _):
        create_payment(paid_usd=Decimal("450.00"))
        response = self.client.get(self.url)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="pagamentos-2026-11-20.csv"',
        )
        lines = response.content.decode("utf-8-sig").splitlines()
        self.assertEqual(len(lines), 2)  # header and the payment
        self.assertEqual(lines[1].split(";")[8], "450,00")

    def test_only_reads(self):
        self.assertEqual(self.client.post(self.url).status_code, 405)
