import re
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from src.integrations.exchange_rates import ExchangeRate, ExchangeRateUnavailable
from src.models import Payment, Task
from src.services.payments import LIST_CHANGED
from tests.factories import (
    create_payment,
    create_project,
    create_provider,
    create_task,
)

NOVEMBER = {"inicio": "2026-11-01", "fim": "2026-11-30"}
RATE = ExchangeRate(rate=Decimal("5.35"), quoted_at="2026-11-16 10:00:00")


@contextmanager
def rate_api(**kwargs):
    """Replace the billing page's exchange-rate provider (no network).

    Yields the provider's ``usd_brl`` mock.
    """
    kwargs.setdefault("return_value", RATE)
    usd_brl = mock.Mock(**kwargs)
    with mock.patch(
        "src.views.billing.default_provider", return_value=mock.Mock(usd_brl=usd_brl)
    ):
        yield usd_brl


class BillingViewTests(TestCase):
    url = reverse("tasks:billing")

    def test_the_old_address_keeps_working_with_its_filter(self):
        # The page was "Painel", at /painel/; bookmarks carry the filter.
        response = self.client.get("/painel/?inicio=2026-11-01&valor_hora=90")
        self.assertRedirects(
            response,
            f"{self.url}?inicio=2026-11-01&valor_hora=90",
            fetch_redirect_response=False,
        )

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
            "src.views.billing.timezone.localdate", return_value=date(2026, 11, 16)
        ):
            response = self.client.get(self.url)
        content = response.content.decode()
        self.assertIn('value="2026-11-01"', content)
        self.assertIn('value="2026-11-30"', content)
        self.assertEqual(len(re.findall(r'name="status"[^>]*checked', content)), 4)
        self.assertRegex(content, r'name="pagas"[^>]*checked')  # paid included

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
            with self.assertLogs("src.services.billing", "WARNING"):
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


PRICED = {
    **NOVEMBER,
    "valor_hora": "90",
    "valor_flat": "100",
    "bonus": "40",
    "pagas": "on",
}
DIALOG_OPEN = r"<dialog [^>]*data-open"


def dialog_data(response):
    """The hidden fields of the "Pagar" dialog, as the browser would send them."""
    dialog = re.search(r"<dialog .*?</dialog>", response.content.decode(), re.S).group()
    data = {}
    for name, value in re.findall(
        r'<input type="hidden" name="(\w+)" value="([^"]*)"', dialog
    ):
        data.setdefault(name, []).append(value)
    return data


class BillingPaymentTests(TestCase):
    """The "Pagar" button: record what was received for the tasks shown."""

    url = reverse("tasks:billing")
    pay_url = reverse("tasks:billing_pay")

    def setUp(self):
        self.provider = create_provider("Alignerr")
        project = create_project(name="Portal do Cliente", provider=self.provider)
        self.login = create_task(
            project,
            name="Login",
            status="DONE",
            minutes_spent=300,
            started_on=date(2026, 11, 3),
        )
        self.api = create_task(
            project,
            name="API",
            status="REJECTED",
            minutes_spent=90,
            started_on=date(2026, 11, 4),
        )
        # Paying needs the company that pays.
        self.priced = {**PRICED, "empresa": str(self.provider.pk)}

    def billing(self, params=None):
        with rate_api():
            return self.client.get(self.url, self.priced if params is None else params)

    def pay(self, data, **amounts):
        amounts = {"pago_usd": "600", "pago_brl": "3200", **amounts}
        with rate_api():
            return self.client.post(self.pay_url, {**data, **amounts})

    def test_pay_button_opens_a_dialog_with_the_estimate(self):
        response = self.billing()
        self.assertContains(response, '<button type="button" id="open-payment">')
        self.assertContains(response, "A pagar:</strong> 2 tarefas")
        # Login 460 + API 135 + bonus 40 = 635; x 5.35
        for label, value in (
            ("Estimado em dólar", "US$ 635.00"),
            ("Estimado em real", "R$ 3.397,25"),
        ):
            with self.subTest(label=label):
                self.assertContains(
                    response, f"<dt>{label}</dt><dd>{value}</dd>", html=True
                )
        self.assertContains(response, 'name="pago_usd"')
        self.assertContains(response, 'name="pago_brl"')
        self.assertEqual(
            sorted(dialog_data(response)["tarefas"]),
            sorted([str(self.login.pk), str(self.api.pk)]),
        )
        self.assertNotRegex(response.content.decode(), DIALOG_OPEN)

    def test_no_pay_button_without_values(self):
        response = self.billing(NOVEMBER)
        self.assertNotContains(response, "open-payment")

    def test_paying_marks_the_tasks_as_paid_and_keeps_the_filter(self):
        response = self.pay(dialog_data(self.billing()))

        payment = Payment.objects.get()
        self.assertEqual(set(payment.tasks.all()), {self.login, self.api})
        self.assertEqual(
            (payment.estimated_usd, payment.paid_usd, payment.paid_brl),
            (Decimal("635.00"), Decimal("600.00"), Decimal("3200.00")),
        )
        self.assertRedirects(
            response,
            f"{self.url}?empresa={self.provider.pk}&inicio=2026-11-01&fim=2026-11-30&"
            "status=DOING&status=REVIEW&status=DONE&status=REJECTED&pagas=True&"
            "valor_hora=90&valor_flat=100&bonus=40",
            fetch_redirect_response=False,
        )
        with rate_api():
            page = self.client.get(response.url)
        self.assertContains(
            page, "Pagamento registrado: 2 tarefa(s), US$ 600.00 e R$ 3.200,00."
        )
        # Everything is paid now: each task is tagged, and no button.
        self.assertContains(page, '<span class="status paid">Pago</span>', count=2)
        self.assertNotContains(page, "open-payment")

    def test_tasks_paid_before_are_tagged_and_left_out(self):
        create_payment(self.api)
        response = self.billing()
        self.assertContains(response, '<span class="status paid">Pago</span>', count=1)
        self.assertContains(response, "(1 já paga fica de fora)")
        self.assertNotContains(response, "As tarefas já pagas estão ocultas.")
        self.assertEqual(dialog_data(response)["tarefas"], [str(self.login.pk)])

    def test_unchecking_paid_tasks_hides_them_from_the_list_and_totals(self):
        create_payment(self.api)
        without_paid = {k: v for k, v in self.priced.items() if k != "pagas"}
        response = self.billing(without_paid)
        self.assertNotContains(response, "API")
        self.assertNotContains(response, '<span class="status paid">Pago</span>')
        self.assertContains(response, "As tarefas já pagas estão ocultas.")
        self.assertNotRegex(response.content.decode(), r'name="pagas"[^>]*checked')
        # Login only: 4 x 90 + 100 + bonus 40
        self.assertContains(
            response, '<span class="value">US$ 500.00</span>', html=True
        )
        # What is left to pay is the same either way.
        self.assertEqual(dialog_data(response)["tarefas"], [str(self.login.pk)])
        self.assertEqual(dialog_data(response)["pagas"], ["False"])

    def test_invalid_amounts_reopen_the_dialog_with_the_error(self):
        response = self.pay(dialog_data(self.billing()), pago_brl="")
        self.assertRegex(response.content.decode(), DIALOG_OPEN)
        self.assertContains(response, "Este campo é obrigatório.")
        self.assertContains(response, 'name="pago_usd" value="600"')  # kept
        self.assertFalse(Payment.objects.exists())

    def test_a_changed_list_reloads_the_billing_page_with_a_message(self):
        data = dialog_data(self.billing())
        create_task(self.login.project, name="Nova", started_on=date(2026, 11, 20))
        response = self.pay(data)
        self.assertEqual(response.url.split("?")[0], self.url)
        with rate_api():
            self.assertContains(self.client.get(response.url), LIST_CHANGED)
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(Task.objects.exclude(payment=None).exists())

    def test_without_a_company_there_is_no_pay_button(self):
        response = self.billing(PRICED)  # "Todas as empresas"
        self.assertContains(response, "A pagar:</strong> 2 tarefas")
        self.assertNotContains(response, "open-payment")
        self.assertNotContains(response, "<dialog")
        self.assertContains(
            response, "Para registrar o pagamento, escolha no filtro a empresa"
        )

    def test_paying_without_a_company_is_refused(self):
        data = dialog_data(self.billing())
        data["empresa"] = [""]  # a hand-made request
        response = self.pay(data)
        self.assertContains(response, "Escolha a empresa que está pagando.")
        self.assertFalse(Payment.objects.exists())

    def test_tasks_of_projects_without_a_company_are_pointed_out(self):
        no_company = create_project(name="Sem dono")
        day = {"status": "DONE", "started_on": date(2026, 11, 5)}
        create_task(no_company, **day)
        # Paid before companies existed: nothing left to do about it.
        create_payment(create_task(no_company, **day))
        response = self.billing(PRICED)
        self.assertContains(
            response,
            "1 tarefa não paga é de um projeto sem empresa e não pode ser paga.",
        )
        # Choosing a company lists only its tasks: nothing to point out.
        self.assertNotContains(self.billing(), "sem empresa e não pode")

    def test_only_post_is_allowed(self):
        self.assertEqual(self.client.get(self.pay_url, PRICED).status_code, 405)
