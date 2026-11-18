from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase

from src.domain.pricing import Pricing
from src.integrations.exchange_rates import ExchangeRateUnavailable
from src.models import Payment
from src.services import payments
from src.services.payments import (
    LIST_CHANGED,
    NO_PROVIDER,
    NOTHING_TO_PAY,
    PaymentError,
    payment_history,
    payments_csv,
    register_payment,
)
from tests.factories import (
    create_payment,
    create_project,
    create_provider,
    create_task,
)
from tests.services.test_billing import ALL, FakeExchangeRates


class RegisterPaymentTests(TestCase):
    def setUp(self):
        self.provider = create_provider()
        self.project = create_project(provider=self.provider)
        self.login = create_task(
            self.project,
            name="Login",
            status="DONE",
            minutes_spent=300,
            started_on=date(2026, 11, 3),
        )
        self.api = create_task(
            self.project,
            name="API",
            status="REJECTED",
            minutes_spent=90,
            started_on=date(2026, 11, 4),
        )

    def pay(self, **overrides):
        values = {
            "start": date(2026, 11, 1),
            "end": date(2026, 11, 30),
            "statuses": ALL,
            "pricing": Pricing(Decimal("90"), Decimal("100"), Decimal("40")),
            "exchange_rates": FakeExchangeRates(),
            "task_ids": [self.login.pk, self.api.pk],
            "paid_usd": Decimal("600.00"),
            "paid_brl": Decimal("3200.00"),
            "provider": self.provider,
        }
        values.update(overrides)
        return register_payment(**values)

    def assert_not_paid(self, *tasks):
        for task in tasks:
            task.refresh_from_db()
            self.assertIsNone(task.payment, task.name)

    def test_records_the_payment_and_marks_the_tasks_as_paid(self):
        payment = self.pay()
        payment.refresh_from_db()
        # Login 460 (4 x 90 + 100) + API 135 (rejected: 1.5 x 90) + bonus 40
        self.assertEqual(
            (
                payment.period_start,
                payment.period_end,
                payment.estimated_usd,
                payment.estimated_brl,  # 635 x 5.35
                payment.paid_usd,
                payment.paid_brl,
            ),
            (
                date(2026, 11, 1),
                date(2026, 11, 30),
                Decimal("635.00"),
                Decimal("3397.25"),
                Decimal("600.00"),
                Decimal("3200.00"),
            ),
        )
        self.assertEqual(set(payment.tasks.all()), {self.login, self.api})

    def test_tasks_paid_before_are_left_out(self):
        earlier = create_payment(self.api)
        payment = self.pay(task_ids=[self.login.pk])
        self.api.refresh_from_db()
        self.assertEqual(list(payment.tasks.all()), [self.login])
        self.assertEqual(self.api.payment, earlier)
        self.assertEqual(payment.estimated_usd, Decimal("500.00"))  # 460 + 40

    def test_a_different_list_of_tasks_saves_nothing(self):
        for task_ids in (
            [self.login.pk],  # one missing
            [self.login.pk, self.api.pk, 99999],  # one too many
        ):
            with self.subTest(task_ids=task_ids):
                with self.assertRaisesMessage(PaymentError, str(LIST_CHANGED)):
                    self.pay(task_ids=task_ids)
                self.assertFalse(Payment.objects.exists())
                self.assert_not_paid(self.login, self.api)

    def test_a_task_added_meanwhile_cancels_the_payment(self):
        create_task(self.project, name="Nova", started_on=date(2026, 11, 20))
        with self.assertRaisesMessage(PaymentError, str(LIST_CHANGED)):
            self.pay()
        self.assertFalse(Payment.objects.exists())

    def test_a_task_paid_meanwhile_rolls_everything_back(self):
        # Another request pays API after this one calculated its list.
        real_build = payments.build_billing

        def build_then_pay_api_elsewhere(**kwargs):
            report = real_build(**kwargs)
            create_payment(self.api)
            return report

        with mock.patch.object(
            payments, "build_billing", side_effect=build_then_pay_api_elsewhere
        ):
            with self.assertRaisesMessage(PaymentError, str(LIST_CHANGED)):
                self.pay()
        self.assertEqual(Payment.objects.count(), 1)  # only the other one
        self.assert_not_paid(self.login)

    def test_a_payment_needs_the_company_that_pays(self):
        with self.assertRaisesMessage(PaymentError, str(NO_PROVIDER)):
            self.pay(provider=None)
        self.assertFalse(Payment.objects.exists())
        self.assert_not_paid(self.login, self.api)

    def test_nothing_to_pay(self):
        create_payment(self.login, self.api)
        for values in ({"pricing": None}, {}):  # no valor/h; everything paid
            with self.subTest(values=values):
                with self.assertRaisesMessage(PaymentError, str(NOTHING_TO_PAY)):
                    self.pay(**values)
        self.assertEqual(Payment.objects.count(), 1)

    def test_without_a_rate_the_estimate_in_reais_is_empty(self):
        with self.assertLogs("src.services.billing", "WARNING"):
            payment = self.pay(
                exchange_rates=FakeExchangeRates(error=ExchangeRateUnavailable("x"))
            )
        payment.refresh_from_db()
        self.assertEqual(
            (payment.estimated_usd, payment.estimated_brl),
            (Decimal("635.00"), None),
        )


class PaymentHistoryTests(TestCase):
    def setUp(self):
        project = create_project()
        self.september = create_payment(
            create_task(project, name="Login", minutes_spent=300),
            create_task(project, name="API", minutes_spent=90),
            period_start=date(2026, 9, 1),
            estimated_usd=Decimal("635.00"),
            estimated_brl=Decimal("3397.25"),
            paid_usd=Decimal("600.00"),
            paid_brl=Decimal("3200.00"),
        )
        self.october = create_payment(
            period_start=date(2026, 10, 1),
            estimated_usd=Decimal("100.00"),
            estimated_brl=Decimal("535.00"),
            paid_usd=Decimal("110.00"),
            paid_brl=Decimal("580.00"),
        )

    def test_newest_first_with_their_tasks_and_hours(self):
        history = payment_history()
        self.assertEqual(history.payments, [self.october, self.september])
        self.assertEqual(
            [(p.task_count, p.minutes) for p in history.payments], [(0, 0), (2, 390)]
        )
        self.assertEqual(
            {task.name for task in history.payments[1].tasks.all()}, {"Login", "API"}
        )

    def test_totals_of_every_payment(self):
        totals = payment_history().totals
        self.assertEqual(
            (
                totals.count,
                totals.estimated_usd,
                totals.paid_usd,
                totals.difference_usd,
                totals.estimated_brl,
                totals.paid_brl,
                totals.difference_brl,
            ),
            (
                2,
                Decimal("735.00"),
                Decimal("710.00"),
                Decimal("-25.00"),
                Decimal("3932.25"),
                Decimal("3780.00"),
                Decimal("-152.25"),
            ),
        )

    def test_no_total_estimate_in_reais_if_one_is_missing(self):
        create_payment(estimated_brl=None)
        totals = payment_history().totals
        self.assertEqual((totals.estimated_brl, totals.difference_brl), (None, None))

    def test_no_payments(self):
        self.september.delete()
        self.october.delete()
        history = payment_history()
        self.assertEqual(
            (
                history.payments,
                history.totals.count,
                history.totals.paid_usd,
                history.totals.estimated_brl,
            ),
            ([], 0, Decimal("0.00"), Decimal("0.00")),
        )


class PaymentHistoryPaginationTests(TestCase):
    """10 payments per page; the totals still cover every payment."""

    def setUp(self):
        # Payment n (1..23) was paid US$ n; the 23rd is the newest.
        self.payments = [
            create_payment(paid_usd=Decimal(n), estimated_usd=Decimal(n))
            for n in range(1, 24)
        ]

    def paid(self, history):
        return [int(payment.paid_usd) for payment in history.payments]

    def test_ten_per_page_newest_first(self):
        self.assertEqual(self.paid(payment_history()), list(range(23, 13, -1)))
        self.assertEqual(self.paid(payment_history(2)), list(range(13, 3, -1)))
        self.assertEqual(self.paid(payment_history(3)), [3, 2, 1])

    def test_totals_cover_every_payment_and_page_totals_only_the_page(self):
        history = payment_history(3)
        self.assertEqual(
            (history.totals.count, history.totals.paid_usd),
            (23, Decimal("276.00")),  # 1 + 2 + ... + 23
        )
        self.assertEqual(
            (history.page_totals.count, history.page_totals.paid_usd),
            (3, Decimal("6.00")),
        )

    def test_an_invalid_page_gives_the_first_or_the_last(self):
        for number, expected in (("abc", 1), ("", 1), (None, 1), ("99", 3), ("-1", 3)):
            with self.subTest(number=number):
                self.assertEqual(payment_history(number).page.number, expected)


class PaymentsCsvTests(TestCase):
    def test_every_payment_newest_first_with_its_tasks_and_hours(self):
        project = create_project()
        create_payment(create_task(project, minutes_spent=300), paid_usd=Decimal("1"))
        for n in range(2, 13):  # more than one page of the list
            create_payment(paid_usd=Decimal(n))
        lines = payments_csv().splitlines()[1:]
        self.assertEqual(
            [line.split(";")[8] for line in lines],  # paid (US$)
            [f"{n},00" for n in range(12, 0, -1)],
        )
        self.assertEqual(lines[-1].split(";")[4:6], ["1", "5,00"])  # tasks, hours
