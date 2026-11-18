from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from src.domain.periods import Grouping, buckets
from src.domain.statistics import PaymentRecord, TaskRecord, compute_statistics

OCT_NOV = buckets(date(2026, 10, 1), date(2026, 11, 30), Grouping.MONTH)


def task(day, minutes=60, status="DONE", paid=False, project="Portal", provider=None):
    return TaskRecord(day, minutes, status, paid, project, provider)


def payment(day, usd, minutes=60):
    return PaymentRecord(day, Decimal(usd), minutes)


class ComputeStatisticsTests(SimpleTestCase):
    def test_tasks_count_in_the_month_they_started(self):
        stats = compute_statistics(
            OCT_NOV,
            tasks=[
                task(date(2026, 10, 31), 90, paid=True),
                task(date(2026, 11, 1), 30, status="DOING"),
                task(date(2026, 11, 30), 60, status="REJECTED", paid=True),
            ],
            payments=[],
        )
        october, november = stats.buckets
        self.assertEqual(
            (october.minutes, october.paid_minutes, october.unpaid_minutes), (90, 90, 0)
        )
        self.assertEqual(
            (november.minutes, november.paid_minutes, november.unpaid_minutes),
            (90, 60, 30),
        )
        self.assertEqual(
            november.tasks_by_status,
            {"DOING": 1, "REVIEW": 0, "DONE": 0, "REJECTED": 1},
        )
        self.assertEqual((october.tasks, november.tasks), (1, 2))

    def test_money_counts_in_the_month_the_payment_was_registered(self):
        stats = compute_statistics(
            OCT_NOV,
            tasks=[],
            payments=[
                payment(date(2026, 10, 5), "100.00"),
                payment(date(2026, 11, 5), "250.50"),
                payment(date(2026, 11, 20), "49.50"),
            ],
        )
        self.assertEqual(
            [bucket.received_usd for bucket in stats.buckets],
            [Decimal("100.00"), Decimal("300.00")],
        )

    def test_totals_of_the_period(self):
        stats = compute_statistics(
            OCT_NOV,
            tasks=[
                task(date(2026, 10, 1), 120, paid=True),
                task(date(2026, 11, 1), 60, status="DONE"),
                task(date(2026, 11, 2), 30, status="REVIEW"),
            ],
            payments=[payment(date(2026, 11, 5), "300.00", minutes=120)],
        )
        self.assertEqual(
            (
                stats.minutes,
                stats.paid_minutes,
                stats.unpaid_minutes,
                stats.tasks,
                stats.done_tasks,
                stats.payments,
                stats.received_usd,
            ),
            (210, 120, 90, 3, 2, 1, Decimal("300.00")),
        )
        self.assertFalse(stats.empty)

    def test_hours_by_project(self):
        stats = compute_statistics(
            OCT_NOV,
            tasks=[
                task(date(2026, 10, 1), 60, project="Portal"),
                task(date(2026, 11, 1), 30, project="API"),
                task(date(2026, 11, 2), 15, project="Portal"),
            ],
            payments=[],
        )
        self.assertEqual(stats.minutes_by_project, {"Portal": 75, "API": 30})

    def test_hours_by_company(self):
        stats = compute_statistics(
            OCT_NOV,
            tasks=[
                task(date(2026, 10, 1), 60, provider="Alignerr"),
                task(date(2026, 11, 1), 30, provider="Etho"),
                task(date(2026, 11, 2), 15, provider="Alignerr"),
                task(date(2026, 11, 3), 10),  # a project without a company
            ],
            payments=[],
        )
        self.assertEqual(
            stats.minutes_by_provider, {"Alignerr": 75, "Etho": 30, None: 10}
        )

    def test_average_is_received_per_hour_of_the_paid_tasks(self):
        for payments, average in (
            # US$ 300 for 2h + US$ 100 for 2h -> US$ 400 / 4h
            (
                [
                    payment(date(2026, 11, 5), 300, 120),
                    payment(date(2026, 11, 6), 100, 120),
                ],
                Decimal("100.00"),
            ),
            ([payment(date(2026, 11, 5), 100, 45)], Decimal("133.33")),  # rounded
            ([payment(date(2026, 11, 5), 100, 0)], None),  # no hours paid
            ([], None),
        ):
            with self.subTest(payments=payments):
                stats = compute_statistics(OCT_NOV, tasks=[], payments=payments)
                self.assertEqual(stats.average_hourly_usd, average)

    def test_records_outside_the_buckets_are_ignored(self):
        stats = compute_statistics(
            OCT_NOV,
            tasks=[task(date(2026, 9, 30))],
            payments=[payment(date(2026, 12, 1), 100)],
        )
        self.assertEqual((stats.tasks, stats.payments), (0, 0))
        self.assertEqual(stats.minutes_by_project, {})
        self.assertTrue(stats.empty)
