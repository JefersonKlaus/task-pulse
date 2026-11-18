from decimal import Decimal

from django.test import TestCase

from src.models import Payment
from tests.factories import (
    create_payment,
    create_project,
    create_provider,
    create_task,
)


class PaymentTests(TestCase):
    def test_names_its_period(self):
        self.assertEqual(str(create_payment()), "Pagamento de 01/11/2026 a 30/11/2026")

    def test_deleting_a_payment_makes_its_tasks_unpaid(self):
        task = create_task()
        create_payment(task).delete()
        task.refresh_from_db()
        self.assertIsNone(task.payment)

    def test_difference_is_paid_minus_estimated(self):
        payment = create_payment(
            estimated_usd=Decimal("635.00"),
            paid_usd=Decimal("600.00"),
            estimated_brl=Decimal("3397.25"),
            paid_brl=Decimal("3200.00"),
        )
        self.assertEqual(
            (payment.difference_usd, payment.difference_brl),
            (Decimal("-35.00"), Decimal("-197.25")),
        )

    def test_no_difference_in_reais_without_an_estimate(self):
        self.assertIsNone(create_payment(estimated_brl=None).difference_brl)


class PaymentProviderTests(TestCase):
    """A payment's company is the company of all its tasks' projects."""

    def setUp(self):
        self.alignerr, self.etho = create_provider("Alignerr"), create_provider("Etho")
        self.alignerr_project = create_project(provider=self.alignerr)
        self.etho_project = create_project(provider=self.etho)
        self.no_company_project = create_project()

    def payment_with_tasks_of(self, *projects):
        return create_payment(*(create_task(project) for project in projects))

    def test_company_name_and_filter_agree(self):
        alignerr, etho, none = (
            self.alignerr_project,
            self.etho_project,
            self.no_company_project,
        )
        # case: (its tasks' projects, company name, mixes companies)
        cases = {
            "Alignerr only": ((alignerr, alignerr), "Alignerr", False),
            "two companies": ((alignerr, etho), None, True),
            "a company and none": ((alignerr, none), None, True),
            "no company": ((none,), None, False),
            "no tasks": ((), None, False),
        }
        payments = {
            case: self.payment_with_tasks_of(*projects)
            for case, (projects, _, _) in cases.items()
        }
        totals = {p.pk: p for p in Payment.objects.with_task_totals()}
        of_alignerr = set(Payment.objects.of_provider(self.alignerr))
        for case, (_, name, mixed) in cases.items():
            payment = totals[payments[case].pk]
            with self.subTest(case=case):
                self.assertEqual(payment.provider_name, name)
                self.assertIs(payment.mixes_providers, mixed)
                self.assertIs(payment in of_alignerr, name == "Alignerr")

    def test_follows_the_company_of_its_projects(self):
        # Payments made before the project had a company get it afterwards.
        payment = self.payment_with_tasks_of(self.no_company_project)
        self.no_company_project.provider = self.etho
        self.no_company_project.save()
        self.assertEqual(list(Payment.objects.of_provider(self.etho)), [payment])

    def test_without_a_company_every_payment(self):
        payments = [
            self.payment_with_tasks_of(project)
            for project in (self.alignerr_project, self.no_company_project)
        ]
        self.assertEqual(set(Payment.objects.of_provider(None)), set(payments))
