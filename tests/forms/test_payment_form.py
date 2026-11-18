from decimal import Decimal
from types import SimpleNamespace

from django.test import TestCase

from src.domain.pricing import Pricing
from src.forms import BillingForm, PaymentForm
from tests.factories import create_provider

FILTER = {"inicio": "2026-11-01", "fim": "2026-11-30", "valor_hora": "90"}


class PaymentFormTests(TestCase):
    def setUp(self):
        self.provider = create_provider()

    def form(self, **data):
        values = {
            **FILTER,
            "empresa": str(self.provider.pk),
            "tarefas": ["3", "7"],
            "pago_usd": "600",
            "pago_brl": "3200",
        }
        values.update(data)
        return PaymentForm(data=values)

    def test_the_company_that_pays_is_required(self):
        self.assertEqual(
            self.form(empresa="").errors["empresa"],
            ["Escolha a empresa que está pagando."],
        )

    def test_reads_the_filter_the_tasks_and_the_amounts(self):
        valid = self.form()
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertEqual(
            (
                valid.cleaned_data["tarefas"],
                valid.cleaned_data["pago_usd"],
                valid.cleaned_data["pago_brl"],
                valid.pricing(),
            ),
            ([3, 7], Decimal("600"), Decimal("3200"), Pricing(Decimal("90"))),
        )

    def test_both_amounts_are_required_and_not_negative(self):
        for amount, message in (
            ("", "Este campo é obrigatório."),
            ("-1", "Certifique-se que este valor seja maior ou igual a 0."),
        ):
            with self.subTest(amount=amount):
                errors = self.form(pago_usd=amount, pago_brl=amount).errors
                self.assertEqual(
                    (errors["pago_usd"], errors["pago_brl"]), ([message], [message])
                )

    def test_task_ids_must_be_sent(self):
        for ids, message in (
            ([], "Não há tarefas a pagar."),
            (["3", "x"], "Lista de ids inválida."),
        ):
            with self.subTest(ids=ids):
                self.assertEqual(self.form(tarefas=ids).errors["tarefas"], [message])

    def test_the_dialog_sends_back_the_filter_on_screen_and_its_tasks(self):
        filter_form = BillingForm(
            data={**FILTER, "status": ["DONE", "REVIEW"], "bonus": "40"}
        )
        self.assertTrue(filter_form.is_valid(), filter_form.errors)
        report = SimpleNamespace(
            to_pay=SimpleNamespace(
                lines=[SimpleNamespace(task=SimpleNamespace(pk=pk)) for pk in (3, 7)]
            )
        )
        html = "".join(
            str(field) for field in PaymentForm.for_report(filter_form, report)
        )
        for hidden in (
            'name="inicio" value="2026-11-01"',
            'name="fim" value="2026-11-30"',
            'name="status" value="REVIEW"',
            'name="status" value="DONE"',
            'name="valor_hora" value="90"',
            'name="bonus" value="40"',
            'name="tarefas" value="3"',
            'name="tarefas" value="7"',
        ):
            with self.subTest(hidden=hidden):
                self.assertRegex(html, rf'<input type="hidden" {hidden}')
        # Its inputs don't reuse the ids of the filter form on the same page.
        self.assertNotIn('id="id_inicio"', html)
