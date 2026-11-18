from datetime import date, datetime, timezone
from decimal import Decimal

from django.test import TestCase

from src.domain.periods import Grouping
from src.models import Payment
from src.services.statistics import build_statistics
from tests.factories import create_payment, create_project, create_task


def registered_at(payment, moment):
    Payment.objects.filter(pk=payment.pk).update(created_at=moment)


class BuildStatisticsTests(TestCase):
    def build(self, grouping=Grouping.MONTH):
        return build_statistics(
            start=date(2026, 10, 1), end=date(2026, 11, 30), grouping=grouping
        )

    def test_reads_the_tasks_started_in_the_period(self):
        portal, api = create_project(name="Portal"), create_project(name="API")
        paid = create_task(portal, minutes_spent=120, started_on=date(2026, 10, 10))
        create_payment(paid)
        create_task(api, minutes_spent=30, started_on=date(2026, 11, 30))
        create_task(portal, minutes_spent=999, started_on=date(2026, 9, 30))  # before
        stats = self.build()
        self.assertEqual(
            [(b.minutes, b.paid_minutes) for b in stats.buckets], [(120, 120), (30, 0)]
        )
        self.assertEqual(stats.minutes_by_project, {"Portal": 120, "API": 30})

    def test_reads_the_payments_registered_in_the_period_in_local_time(self):
        project = create_project()
        november = create_payment(
            create_task(project, minutes_spent=60), paid_usd=Decimal("90.00")
        )
        december = create_payment(paid_usd=Decimal("1000.00"))
        # 01:00 UTC on 1 December is still 30 November in São Paulo (UTC-3).
        registered_at(november, datetime(2026, 12, 1, 1, 0, tzinfo=timezone.utc))
        registered_at(december, datetime(2026, 12, 1, 4, 0, tzinfo=timezone.utc))
        stats = self.build()
        self.assertEqual(
            [b.received_usd for b in stats.buckets], [Decimal("0.00"), Decimal("90.00")]
        )
        self.assertEqual(
            (stats.payments, stats.average_hourly_usd), (1, Decimal("90.00"))
        )

    def test_a_period_from_mid_month_leaves_out_the_days_before_it(self):
        # The whole of October is one bar, but only from the 15th counts.
        before = create_payment(paid_usd=Decimal("500.00"))
        inside = create_payment(paid_usd=Decimal("70.00"))
        registered_at(before, datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc))
        registered_at(inside, datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))
        create_task(minutes_spent=999, started_on=date(2026, 10, 14))
        create_task(minutes_spent=60, started_on=date(2026, 10, 15))
        stats = build_statistics(
            start=date(2026, 10, 15), end=date(2026, 11, 30), grouping=Grouping.MONTH
        )
        october = stats.buckets[0]
        self.assertEqual(
            (october.received_usd, october.minutes), (Decimal("70.00"), 60)
        )

    def test_by_week(self):
        create_task(minutes_spent=60, started_on=date(2026, 11, 30))
        stats = self.build(Grouping.WEEK)
        self.assertEqual(stats.buckets[0].bucket.label, "28/09")
        self.assertEqual(
            (stats.buckets[-1].bucket.label, stats.buckets[-1].minutes), ("30/11", 60)
        )
