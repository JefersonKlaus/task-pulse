from datetime import date

from django.test import SimpleTestCase

from src.domain.periods import month_of


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
