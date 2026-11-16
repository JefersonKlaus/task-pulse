from decimal import Decimal

from django.test import SimpleTestCase

from src.domain.money import format_brl, format_rate, format_usd, usd_to_brl


class MoneyFormatTests(SimpleTestCase):
    """Each currency is written its own way, whatever the page locale."""

    def test_dollars_us_style(self):
        self.assertEqual(format_usd(Decimal("1234567.5")), "US$ 1,234,567.50")

    def test_reais_brazilian_style(self):
        self.assertEqual(format_brl(Decimal("1234567.5")), "R$ 1.234.567,50")

    def test_rate_with_four_decimals(self):
        self.assertEqual(format_rate(Decimal("5.35214")), "R$ 5,3521")


class UsdToBrlTests(SimpleTestCase):
    def test_converts_and_rounds_half_up_to_cents(self):
        self.assertEqual(
            usd_to_brl(Decimal("460"), Decimal("5.35")), Decimal("2461.00")
        )
        self.assertEqual(usd_to_brl(Decimal("1"), Decimal("5.345")), Decimal("5.35"))
