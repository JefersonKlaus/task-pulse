from decimal import Decimal

from django.test import SimpleTestCase

from src.domain.period_summary import summarize
from src.domain.pricing import Pricing
from tests.factories import build_task


def tasks():
    return [
        build_task(name="Login", status="DONE", minutes_spent=300),
        build_task(name="API", status="REJECTED", minutes_spent=120),
        build_task(name="Deploy", status="DOING", minutes_spent=30),
    ]


class SummarizeTests(SimpleTestCase):
    def test_hours_and_totals_per_status(self):
        summary = summarize(tasks(), statuses=["DONE", "REJECTED"])
        self.assertEqual(summary.minutes, 450)
        self.assertEqual(
            [(s.label, s.tasks, s.minutes) for s in summary.by_status],
            [("Done", 1, 300), ("Rejeitado", 1, 120)],
        )

    def test_without_pricing_there_is_no_money(self):
        summary = summarize(tasks())
        self.assertIsNone(summary.total_usd)
        self.assertEqual({line.value for line in summary.lines}, {None})

    def test_value_of_each_task_and_total(self):
        summary = summarize(tasks(), Pricing(Decimal("90"), Decimal("100")))
        self.assertEqual(
            [line.value for line in summary.lines],
            [Decimal("460.00"), Decimal("180.00"), Decimal("50.00")],
        )
        self.assertEqual(summary.total_usd, Decimal("690.00"))

    def test_bonus_is_added_once_to_the_total(self):
        summary = summarize(
            tasks(), Pricing(Decimal("90"), Decimal("100"), bonus=Decimal("40"))
        )
        self.assertEqual(
            (summary.tasks_usd, summary.bonus_usd, summary.total_usd),
            (Decimal("690.00"), Decimal("40.00"), Decimal("730.00")),
        )

    def test_total_is_the_sum_of_the_rounded_rows(self):
        # Each 1-minute task at $1/h is 0.0166 -> 0.02, so the total is 0.06.
        summary = summarize(
            [build_task(minutes_spent=1) for _ in range(3)], Pricing(Decimal("1"))
        )
        self.assertEqual(summary.total_usd, Decimal("0.06"))
