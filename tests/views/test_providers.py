from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from src.integrations.exchange_rates import ExchangeRate
from src.models import Payment, Project, Provider
from tests.factories import create_payment, create_project, create_provider, create_task


class ProviderPagesTests(TestCase):
    def test_lists_the_companies_with_their_projects(self):
        alignerr = create_provider("Alignerr")
        create_project(provider=alignerr)
        create_project(provider=alignerr)
        create_provider("Etho")
        response = self.client.get(reverse("tasks:provider_list"))
        self.assertContains(response, "2 projetos")
        self.assertContains(response, "0 projetos")
        # A company opens its projects.
        self.assertContains(
            response, f'href="{reverse("tasks:project_list")}?empresa={alignerr.pk}"'
        )
        self.assertContains(
            response, reverse("tasks:provider_update", args=[alignerr.pk])
        )

    def test_empty_list_invites_to_add_one(self):
        response = self.client.get(reverse("tasks:provider_list"))
        self.assertContains(response, "Nenhuma empresa cadastrada.")

    def test_creates_and_renames_a_company(self):
        response = self.client.post(reverse("tasks:provider_create"), {"name": "Etho"})
        self.assertRedirects(response, reverse("tasks:provider_list"))
        provider = Provider.objects.get()
        url = reverse("tasks:provider_update", args=[provider.pk])
        self.assertContains(self.client.get(url), 'value="Etho"')
        self.client.post(url, {"name": "Etho AI"})
        provider.refresh_from_db()
        self.assertEqual(provider.name, "Etho AI")

    def test_a_name_in_use_is_refused(self):
        create_provider("Alignerr")
        response = self.client.post(
            reverse("tasks:provider_create"), {"name": "alignerr"}
        )
        self.assertContains(response, "Já existe uma empresa com este nome.")
        self.assertEqual(Provider.objects.count(), 1)


class ProviderFiltersTests(TestCase):
    def setUp(self):
        self.alignerr, self.etho = create_provider("Alignerr"), create_provider("Etho")
        self.portal = create_project(name="Portal", provider=self.alignerr)
        self.api = create_project(name="API", provider=self.etho)
        self.loose = create_project(name="Solto")

    def test_projects_show_and_filter_by_company(self):
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, '<span class="provider-tag">Alignerr</span>')
        self.assertContains(
            response, '<span class="provider-tag none">Sem empresa</span>'
        )
        response = self.client.get(
            reverse("tasks:project_list"), {"empresa": self.etho.pk}
        )
        self.assertContains(response, ">API</strong>")
        self.assertNotContains(response, ">Portal</strong>")
        self.assertContains(response, f'<option value="{self.etho.pk}" selected>')

    def test_an_unknown_company_shows_every_project_and_an_error(self):
        response = self.client.get(reverse("tasks:project_list"), {"empresa": 999})
        self.assertContains(response, ">Portal</strong>")
        self.assertContains(response, "Faça uma escolha válida.")

    def test_no_filter_before_the_first_company(self):
        Provider.objects.all().delete()
        response = self.client.get(reverse("tasks:project_list"))
        self.assertNotContains(response, 'class="list-filter"')

    def test_project_form_and_page_show_the_company(self):
        response = self.client.post(
            reverse("tasks:project_create"),
            {"url": "https://github.com/acme/x", "name": "", "description": "",
             "provider": self.etho.pk},
        )
        project = Project.objects.get(name="x")
        self.assertEqual(project.provider, self.etho)
        response = self.client.get(response.url)
        self.assertContains(response, f"?empresa={self.etho.pk}")
        self.assertContains(response, ">Etho</a>")

    def test_payments_of_a_company_with_its_export_and_pages(self):
        for _ in range(11):  # two pages of Etho payments
            create_payment(create_task(self.api))
        create_payment(create_task(self.portal))
        url = reverse("tasks:payment_list")
        response = self.client.get(url, {"empresa": self.etho.pk})
        self.assertContains(response, "Mostrando 1–10 de 11 pagamentos.")
        self.assertContains(
            response, '<span class="provider-tag">Etho</span>', count=10
        )
        self.assertContains(
            response, f'href="?empresa={self.etho.pk}&amp;pagina=2" rel="next"'
        )
        export = f'{reverse("tasks:payment_export")}?empresa={self.etho.pk}'
        self.assertContains(response, f'href="{export}"')
        lines = self.client.get(export).content.decode("utf-8-sig").splitlines()
        self.assertEqual(len(lines), 12)  # header + 11
        empty = self.client.get(url, {"empresa": create_provider("Nova").pk})
        self.assertContains(empty, "Nenhum pagamento desta empresa.")

    def test_a_payment_of_several_companies(self):
        create_payment(create_task(self.api), create_task(self.portal))
        response = self.client.get(reverse("tasks:payment_list"))
        self.assertContains(
            response, '<span class="provider-tag none">Várias empresas</span>'
        )

    def test_billing_of_a_company_and_its_payment(self):
        november = {
            "started_on": date(2026, 11, 5),
            "status": "DONE",
            "minutes_spent": 60,
        }
        etho_task = create_task(self.api, name="Tarefa Etho", **november)
        create_task(self.portal, name="Tarefa Alignerr", **november)
        params = {"empresa": self.etho.pk, "inicio": "2026-11-01", "fim": "2026-11-30",
                  "valor_hora": "90", "pagas": "on"}
        rate = ExchangeRate(rate=Decimal("5"), quoted_at="")
        with mock.patch(
            "src.views.billing.default_provider",
            return_value=mock.Mock(usd_brl=mock.Mock(return_value=rate)),
        ):
            page = self.client.get(reverse("tasks:billing"), params)
            self.assertContains(page, "Tarefa Etho")
            self.assertNotContains(page, "Tarefa Alignerr")
            # The dialog carries the company with the rest of the filter.
            self.assertContains(
                page, f'<input type="hidden" name="empresa" value="{self.etho.pk}"'
            )
            self.client.post(
                reverse("tasks:billing_pay"),
                {
                    **params,
                    "tarefas": [etho_task.pk],
                    "pago_usd": "90",
                    "pago_brl": "450",
                },
            )
        payment = Payment.objects.get()
        self.assertEqual(list(payment.tasks.all()), [etho_task])

    def test_statistics_of_a_company_and_hours_by_company(self):
        create_task(self.api, minutes_spent=60, started_on=date(2026, 11, 5))
        create_task(self.portal, minutes_spent=120, started_on=date(2026, 11, 5))
        params = {"inicio": "2026-11-01", "fim": "2026-11-30", "agrupar": "mes"}
        every = self.client.get(reverse("tasks:statistics"), params)
        self.assertContains(every, "Horas por empresa")
        self.assertContains(every, '<span class="value">3.00h</span>', html=True)
        etho = self.client.get(
            reverse("tasks:statistics"), {**params, "empresa": self.etho.pk}
        )
        self.assertContains(etho, '<span class="value">1.00h</span>', html=True)
        self.assertNotContains(etho, "Horas por empresa")

    def test_import_gives_new_projects_the_company(self):
        upload = SimpleUploadedFile(
            "t.csv",
            b"date;id;time;desc;status;github\n16/11/2026;1;1;Login;DONE;acme/mobile\n",
        )
        self.client.post(
            reverse("tasks:task_import"), {"file": upload, "provider": self.alignerr.pk}
        )
        self.assertEqual(Project.objects.get(name="mobile").provider, self.alignerr)
