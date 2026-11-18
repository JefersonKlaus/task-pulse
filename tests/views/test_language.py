from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from src.domain.periods import Grouping, buckets
from src.integrations.tasks_csv import ImportFileError, read_tasks_file
from tests.factories import create_project

SWITCH = reverse("set_language")


class LanguageTests(TestCase):
    """The interface is in Portuguese or English (the switch at the top)."""

    def test_portuguese_by_default(self):
        response = self.client.get(reverse("tasks:payment_list"))
        self.assertContains(response, '<html lang="pt-br">')
        self.assertContains(response, "<h1>Pagamentos</h1>")
        self.assertContains(response, 'value="pt-br" lang="pt-br"')
        self.assertContains(response, 'aria-pressed="true" class="current">PT</button>')

    def test_switching_keeps_the_page_and_is_remembered(self):
        page = f"{reverse('tasks:statistics')}?inicio=2026-01-01&fim=2026-11-30"
        response = self.client.post(SWITCH, {"language": "en", "next": page})
        self.assertRedirects(response, page, fetch_redirect_response=False)
        response = self.client.get(page)
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "<h1>Statistics</h1>")
        self.assertContains(response, ">Billing</a>")  # the menu
        self.assertContains(response, 'aria-pressed="true" class="current">EN</button>')
        # Back to Portuguese.
        self.client.post(SWITCH, {"language": "pt-br", "next": page})
        self.assertContains(self.client.get(page), "<h1>Estatísticas</h1>")

    def test_the_switch_returns_to_the_same_address(self):
        page = reverse("tasks:payment_list") + "?pagina=2"
        response = self.client.get(page)
        self.assertContains(
            response, f'<input type="hidden" name="next" value="{page}">'
        )

    def test_the_browser_language_until_one_is_chosen(self):
        url = reverse("tasks:project_list")
        english_browser = {"HTTP_ACCEPT_LANGUAGE": "en-US,en;q=0.9"}
        response = self.client.get(url, **english_browser)
        self.assertContains(response, "<h1>Projects</h1>")
        self.client.post(SWITCH, {"language": "pt-br", "next": url})
        response = self.client.get(url, **english_browser)
        self.assertContains(response, "<h1>Projetos</h1>")

    def test_messages_and_errors_in_english(self):
        self.client.post(SWITCH, {"language": "en", "next": "/"})
        upload = SimpleUploadedFile(
            "t.csv", b"date;id;time;desc;status\n31/02/2026;A;1;Login;DONE\n"
        )
        response = self.client.post(
            reverse("tasks:task_import"),
            {"file": upload, "project": create_project().pk},
        )
        self.assertContains(
            response, "Line 2: invalid date “31/02/2026” (use dd/mm/yyyy)."
        )


class EnglishTextsTests(TestCase):
    def test_chart_months(self):
        def labels():
            months = buckets(date(2026, 1, 1), date(2026, 2, 1), Grouping.MONTH)
            return [month.label for month in months]

        self.assertEqual(labels(), ["jan/26", "fev/26"])
        with translation.override("en"):
            self.assertEqual(labels(), ["Jan/26", "Feb/26"])

    def test_the_csv_format_does_not_change_with_the_language(self):
        # "Rejeitado" is a word of the file format, not a translated label.
        data = b"date;id;time;desc;status\n16/11/2026;A;1;Login;Rejeitado\n"
        with translation.override("en"):
            (row,) = read_tasks_file(data)
            with self.assertRaises(ImportFileError) as raised:
                read_tasks_file(b"date;id;time;desc;status\n16/11/2026;A;1;Login;x\n")
        self.assertEqual(row.status, "REJECTED")
        self.assertEqual(
            raised.exception.messages,
            ["Line 2: invalid status “x” (use DOING, REVIEW, DONE, REJECTED)."],
        )
