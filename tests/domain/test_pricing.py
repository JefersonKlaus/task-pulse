from decimal import Decimal

from django.test import SimpleTestCase

from src.domain.pricing import Pricing


class PricingTests(SimpleTestCase):
    """Valor/h pays every hour; the flat rate pays the last hour of tasks
    that were not rejected."""

    def test_value_of_a_task(self):
        for minutes, status, flat, expected in (
            (300, "DONE", None, "450.00"),  # 5 x 90
            (300, "DONE", "100", "460.00"),  # 4 x 90 + 1 x 100
            (270, "DONE", "100", "415.00"),  # 3.5 x 90 + 1 x 100
            (45, "DONE", "100", "75.00"),  # under an hour: all flat
            (300, "DOING", "100", "460.00"),  # any status but REJECTED
            (300, "REJECTED", "100", "450.00"),  # never flat
            (0, "DONE", "100", "0.00"),
        ):
            pricing = Pricing(Decimal("90"), Decimal(flat) if flat else None)
            with self.subTest(minutes=minutes, status=status, flat=flat):
                self.assertEqual(pricing.task_value(minutes, status), Decimal(expected))

    def test_rounds_to_cents(self):
        # 1 minute at $90.55/h = 1.50916...
        self.assertEqual(
            Pricing(Decimal("90.55")).task_value(1, "DONE"), Decimal("1.51")
        )
