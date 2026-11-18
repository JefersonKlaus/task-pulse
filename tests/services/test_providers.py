"""The company filter in every service (the rules are tested in the models)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from django.test import TestCase

from src.domain.periods import Grouping
from src.domain.pricing import Pricing
from src.integrations.tasks_csv import ImportedRow
from src.models import Payment, Project
from src.services.billing import build_billing
from src.services.payments import payment_history, payments_csv, register_payment
from src.services.statistics import build_statistics
from src.services.task_import import NewProject, import_tasks
from tests.factories import create_payment, create_project, create_provider, create_task
from tests.services.test_billing import ALL, FakeExchangeRates

NOVEMBER = {"start": date(2026, 11, 1), "end": date(2026, 11, 30)}


class ProviderFilterTests(TestCase):
    def setUp(self):
        self.alignerr, self.etho = create_provider("Alignerr"), create_provider("Etho")
        alignerr_project = create_project(name="Portal", provider=self.alignerr)
        etho_project = create_project(name="API", provider=self.etho)
        day = {"started_on": date(2026, 11, 5), "status": "DONE"}
        self.alignerr_task = create_task(alignerr_project, minutes_spent=120, **day)
        self.etho_task = create_task(etho_project, minutes_spent=60, **day)

    def test_billing_lists_only_the_company_tasks(self):
        report = build_billing(
            **NOVEMBER,
            statuses=ALL,
            pricing=None,
            exchange_rates=FakeExchangeRates(),
            provider=self.alignerr,
        )
        self.assertEqual(
            [line.task for line in report.summary.lines], [self.alignerr_task]
        )

    def test_a_payment_of_a_company_pays_only_its_tasks(self):
        payment = register_payment(
            **NOVEMBER,
            statuses=ALL,
            pricing=Pricing(Decimal("90"), None, None),
            exchange_rates=FakeExchangeRates(),
            task_ids=[self.etho_task.pk],
            paid_usd=Decimal("90.00"),
            paid_brl=Decimal("480.00"),
            provider=self.etho,
        )
        self.assertEqual(list(payment.tasks.all()), [self.etho_task])
        self.assertEqual(payment.estimated_usd, Decimal("90.00"))  # 1h x 90

    def test_payment_history_and_export_of_a_company(self):
        etho_payment = create_payment(self.etho_task, paid_usd=Decimal("90.00"))
        create_payment(self.alignerr_task, paid_usd=Decimal("180.00"))
        history = payment_history(provider=self.etho)
        self.assertEqual(history.payments, [etho_payment])
        self.assertEqual(
            (history.totals.count, history.totals.paid_usd), (1, Decimal("90.00"))
        )
        self.assertEqual(history.payments[0].provider_name, "Etho")
        lines = payments_csv(self.etho).splitlines()[1:]
        self.assertEqual([line.split(";")[1] for line in lines], ["Etho"])
        self.assertEqual(len(payments_csv().splitlines()), 3)  # header + 2

    def test_statistics_of_a_company_and_hours_by_company(self):
        payment = create_payment(self.etho_task, paid_usd=Decimal("90.00"))
        Payment.objects.filter(pk=payment.pk).update(
            created_at=datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
        )
        create_task(minutes_spent=30, started_on=date(2026, 11, 6))  # no company
        period = {**NOVEMBER, "grouping": Grouping.MONTH}
        every = build_statistics(**period)
        self.assertEqual(
            every.minutes_by_provider, {"Alignerr": 120, "Etho": 60, None: 30}
        )
        etho = build_statistics(**period, provider=self.etho)
        self.assertEqual((etho.minutes, etho.received_usd), (60, Decimal("90.00")))
        alignerr = build_statistics(**period, provider=self.alignerr)
        self.assertEqual((alignerr.minutes, alignerr.payments), (120, 0))


class ImportProviderTests(TestCase):
    def row(self, external_id, github=""):
        return ImportedRow(external_id, date(2026, 11, 5), 60, "Tarefa", "DONE", github)

    def test_new_projects_get_the_company_and_existing_keep_theirs(self):
        alignerr, etho = create_provider("Alignerr"), create_provider("Etho")
        existing = create_project(
            name="api", url="https://github.com/acme/api", provider=etho
        )
        import_tasks(
            [
                self.row("1"),  # the form's new project
                self.row("2", "https://github.com/acme/mobile"),  # created
                self.row("3", "https://github.com/acme/api"),  # existing
            ],
            NewProject(url="https://github.com/acme/portal", provider=alignerr),
            provider=alignerr,
        )
        companies = {p.name: p.provider for p in Project.objects.all()}
        self.assertEqual(
            companies, {"portal": alignerr, "mobile": alignerr, "api": etho}
        )
        existing.refresh_from_db()
        self.assertEqual(existing.provider, etho)
