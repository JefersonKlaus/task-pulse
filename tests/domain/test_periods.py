from datetime import date

from django.test import SimpleTestCase

from src.domain.periods import (
    Grouping,
    bucket_count,
    buckets,
    month_of,
    months_before,
)


class MonthOfTests(SimpleTestCase):
    def test_first_and_last_day_of_the_month(self):
        for day, last in (
            (date(2026, 11, 16), 30),
            (date(2026, 2, 10), 28),
            (date(2028, 2, 10), 29),  # leap year
        ):
            with self.subTest(day=day):
                self.assertEqual(
                    month_of(day), (day.replace(day=1), day.replace(day=last))
                )


class MonthsBeforeTests(SimpleTestCase):
    def test_first_day_of_an_earlier_month(self):
        for day, months, expected in (
            (date(2026, 11, 17), 0, date(2026, 11, 1)),
            (date(2026, 11, 17), 11, date(2025, 12, 1)),
            (date(2026, 3, 31), 1, date(2026, 2, 1)),  # no "February 31"
            (date(2026, 1, 15), 13, date(2024, 12, 1)),
        ):
            with self.subTest(day=day, months=months):
                self.assertEqual(months_before(day, months), expected)


def summary(result):
    return [(bucket.label, bucket.start, bucket.end) for bucket in result]


class BucketsTests(SimpleTestCase):
    def test_months(self):
        self.assertEqual(
            summary(buckets(date(2025, 12, 15), date(2026, 2, 3), Grouping.MONTH)),
            [
                ("dez/25", date(2025, 12, 1), date(2025, 12, 31)),
                ("jan/26", date(2026, 1, 1), date(2026, 1, 31)),
                ("fev/26", date(2026, 2, 1), date(2026, 2, 28)),
            ],
        )

    def test_weeks_go_from_monday_to_sunday(self):
        # 01/11/2026 is a Sunday, so the first week started on 26/10.
        self.assertEqual(
            summary(buckets(date(2026, 11, 1), date(2026, 11, 10), Grouping.WEEK)),
            [
                ("26/10", date(2026, 10, 26), date(2026, 11, 1)),
                ("02/11", date(2026, 11, 2), date(2026, 11, 8)),
                ("09/11", date(2026, 11, 9), date(2026, 11, 15)),
            ],
        )

    def test_count_without_building_them(self):
        for start, end in (
            (date(2026, 11, 1), date(2026, 11, 1)),
            (date(2026, 11, 1), date(2026, 11, 10)),
            (date(2025, 12, 1), date(2026, 11, 30)),
            (date(2024, 2, 29), date(2026, 1, 4)),
        ):
            for grouping in Grouping:
                with self.subTest(start=start, end=end, grouping=grouping):
                    self.assertEqual(
                        bucket_count(start, end, grouping),
                        len(buckets(start, end, grouping)),
                    )

    def test_a_bucket_contains_its_first_and_last_day(self):
        (november,) = buckets(date(2026, 11, 5), date(2026, 11, 6), Grouping.MONTH)
        for day, inside in (
            (date(2026, 10, 31), False),
            (date(2026, 11, 1), True),
            (date(2026, 11, 30), True),
            (date(2026, 12, 1), False),
        ):
            with self.subTest(day=day):
                self.assertIs(day in november, inside)
