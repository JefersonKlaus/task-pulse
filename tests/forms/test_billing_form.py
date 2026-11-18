from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from src.domain.pricing import Pricing
from src.forms import BillingForm

ALL_STATUSES = ["DOING", "REVIEW", "DONE", "REJECTED"]


def form(**data):
    return BillingForm(data={"inicio": "2026-11-01", "fim": "2026-11-30", **data})


class BillingFormTests(SimpleTestCase):
    def test_end_before_start_is_rejected(self):
        self.assertEqual(
            form(fim="2026-10-31").errors["fim"],
            ["A data final não pode ser anterior à inicial."],
        )

    def test_flat_rate_and_bonus_need_an_hourly_rate(self):
        self.assertEqual(
            form(valor_flat="100", bonus="40").errors["valor_hora"],
            [
                "Informe o valor/h para usar o valor flat.",
                "Informe o valor/h para usar o bônus.",
            ],
        )

    def test_an_invalid_hourly_rate_shows_only_its_own_error(self):
        self.assertEqual(
            form(valor_hora="-1", bonus="40").errors["valor_hora"],
            ["Certifique-se que este valor seja maior ou igual a 0."],
        )

    def test_no_status_checked_means_every_status(self):
        valid = form()
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertEqual(valid.cleaned_data["status"], ALL_STATUSES)

    def test_first_visit_is_this_month_with_every_status(self):
        self.assertEqual(
            BillingForm.initial_data(date(2026, 2, 10)),
            {
                "inicio": "2026-02-01",
                "fim": "2026-02-28",
                "status": ALL_STATUSES,
                "pagas": True,
            },
        )

    def test_paid_tasks_are_included_only_when_checked(self):
        # A browser sends nothing for an unchecked box.
        for data, included in (({}, False), ({"pagas": "on"}, True)):
            valid = form(**data)
            with self.subTest(data=data):
                self.assertTrue(valid.is_valid(), valid.errors)
                self.assertIs(valid.cleaned_data["pagas"], included)

    def test_pricing_from_the_rates(self):
        without_rate, with_rates = form(), form(
            valor_hora="90", valor_flat="100", bonus="40"
        )
        self.assertTrue(without_rate.is_valid() and with_rates.is_valid())
        self.assertIsNone(without_rate.pricing())
        self.assertEqual(
            with_rates.pricing(), Pricing(Decimal("90"), Decimal("100"), Decimal("40"))
        )
