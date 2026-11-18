import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal

from django.test import SimpleTestCase

from src.integrations.payments_csv import HEADER, write_payments_csv
from src.models import Payment


def payment(**overrides):
    """An unsaved payment with the totals of ``with_task_totals()``."""
    values = {
        "period_start": date(2026, 11, 1),
        "period_end": date(2026, 11, 30),
        "estimated_usd": Decimal("460.00"),
        "estimated_brl": Decimal("2461.00"),
        "paid_usd": Decimal("450.00"),
        "paid_brl": Decimal("2400.00"),
        # 17:30 UTC is 14:30 in São Paulo (settings.TIME_ZONE).
        "created_at": datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc),
    }
    totals = {
        "task_count": 2,
        "minutes": 465,
        # Its tasks are all of Alignerr's projects.
        "provider_count": 1,
        "tasks_without_provider": 0,
        "any_provider_name": "Alignerr",
    }
    for name in totals:
        if name in overrides:
            totals[name] = overrides.pop(name)
    values.update(overrides)
    instance = Payment(**values)
    for name, value in totals.items():
        setattr(instance, name, value)
    return instance


def rows(text):
    """The lines of the CSV text, as lists of values."""
    return list(csv.reader(io.StringIO(text.removeprefix("\ufeff")), delimiter=";"))


class WritePaymentsCsvTests(SimpleTestCase):
    def test_one_line_per_payment_with_every_column(self):
        self.assertEqual(
            rows(write_payments_csv([payment()])),
            [
                list(HEADER),
                [
                    "17/11/2026 14:30",  # registered, in the app's time zone
                    "Alignerr",  # the company of its tasks
                    "01/11/2026",
                    "30/11/2026",
                    "2",  # tasks
                    "7,75",  # hours (465 minutes)
                    "460,00",
                    "2461,00",
                    "450,00",
                    "2400,00",
                    "-10,00",  # paid - estimated
                    "-61,00",
                ],
            ],
        )

    def test_values_are_plain_numbers_with_a_decimal_comma(self):
        # No currency symbol or thousands separator, so a spreadsheet can
        # add them up.
        (line,) = rows(write_payments_csv([payment(paid_usd=Decimal("12345.60"))]))[1:]
        self.assertEqual(line[8], "12345,60")

    def test_without_an_estimate_in_reais_its_values_are_empty(self):
        (line,) = rows(write_payments_csv([payment(estimated_brl=None)]))[1:]
        self.assertEqual((line[7], line[9], line[11]), ("", "2400,00", ""))

    def test_keeps_the_order_given(self):
        text = write_payments_csv(
            [
                payment(period_start=date(2026, 10, 1)),
                payment(period_start=date(2026, 9, 1)),
            ]
        )
        self.assertEqual(
            [line[2] for line in rows(text)[1:]], ["01/10/2026", "01/09/2026"]
        )

    def test_file_format_for_excel(self):
        text = write_payments_csv([payment()])
        self.assertTrue(text.startswith("\ufeffRegistrado em;Empresa;Início;Fim;"))
        self.assertEqual(text.count("\r\n"), 2)  # header and one payment

    def test_the_company_of_the_tasks(self):
        for totals, company in (
            ({}, "Alignerr"),
            ({"provider_count": 2}, "Várias empresas"),
            ({"tasks_without_provider": 1}, "Várias empresas"),  # some have none
            ({"provider_count": 0, "tasks_without_provider": 2}, ""),
        ):
            with self.subTest(totals=totals):
                (line,) = rows(write_payments_csv([payment(**totals)]))[1:]
                self.assertEqual(line[1], company)

    def test_no_payments_gives_only_the_header(self):
        self.assertEqual(rows(write_payments_csv([])), [list(HEADER)])
