from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from src.forms import TaskImportForm
from src.services.task_import import NewProject
from tests.factories import create_project, create_provider

HEADER = b"date;id;time;desc;status\n"
VALID_CSV = HEADER + b"16/11/2026;TP-1;3,8;Tela de login;DONE\n"


def import_form(data, content=VALID_CSV):
    return TaskImportForm(
        data=data, files={"file": SimpleUploadedFile("t.csv", content, "text/csv")}
    )


class TaskImportFormTests(TestCase):
    def test_needs_a_project_or_a_new_project_url(self):
        self.assertEqual(
            import_form({}).errors["new_project_url"],
            [
                "Informe a URL para criar um projeto novo, "
                "ou escolha um projeto existente."
            ],
        )

    def test_shows_at_most_20_file_errors(self):
        project = create_project()
        for lines, shown, last in (
            (20, 20, "Linha 21: data inválida “xx” (use dd/mm/aaaa)."),
            (25, 21, "… e mais 5 erros."),
        ):
            bad_lines = b"".join(b"xx;ID%d;1;T;DONE\n" % n for n in range(lines))
            errors = import_form({"project": project.pk}, HEADER + bad_lines).errors
            with self.subTest(lines=lines):
                self.assertEqual(
                    (len(errors["file"]), errors["file"][-1]), (shown, last)
                )

    def test_rejects_files_over_the_size_limit(self):
        project = create_project()
        for limit, accepted in ((len(VALID_CSV), True), (len(VALID_CSV) - 1, False)):
            with mock.patch.object(TaskImportForm, "MAX_FILE_SIZE", limit):
                errors = import_form({"project": project.pk}).errors
            with self.subTest(limit=limit):
                self.assertEqual(
                    errors.get("file"),
                    None if accepted else ["O arquivo tem mais de 2 MB."],
                )

    def test_destination_is_the_selected_project(self):
        project = create_project()
        form = import_form(
            {"project": project.pk, "new_project_url": "https://x/ignored"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.destination(), project)

    def test_destination_is_a_new_project(self):
        provider = create_provider()
        form = import_form(
            {
                "new_project_url": "https://github.com/acme/x.git",
                "new_project_name": "Meu",
                "provider": provider.pk,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.destination(),
            NewProject(
                url="https://github.com/acme/x.git", name="Meu", provider=provider
            ),
        )

    def test_a_new_project_needs_its_company(self):
        form = import_form({"new_project_url": "https://github.com/acme/x.git"})
        self.assertEqual(
            form.errors["provider"],
            ["Escolha a empresa dos projetos que serão criados."],
        )

    def test_no_company_needed_when_no_project_is_created(self):
        form = import_form({"project": create_project().pk})
        self.assertTrue(form.is_valid(), form.errors)


class TaskImportFormGithubTests(TestCase):
    GITHUB = b"date;id;time;desc;status;github\n"

    def test_no_project_needed_when_every_row_has_github(self):
        create_project(url="https://github.com/acme/portal")
        form = import_form({}, self.GITHUB + b"16/11/2026;A;1;Login;DONE;acme/portal\n")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.destination())

    def test_a_new_repository_needs_the_company_of_its_project(self):
        csv = self.GITHUB + b"16/11/2026;A;1;Login;DONE;acme/new\n"
        self.assertIn("provider", import_form({}, csv).errors)
        form = import_form({"provider": create_provider().pk}, csv)
        self.assertTrue(form.is_valid(), form.errors)

    def test_rows_without_github_still_need_a_project(self):
        form = import_form(
            {},
            self.GITHUB
            + b"16/11/2026;A;1;Login;DONE;acme/portal\n"
            + b"16/11/2026;B;1;API;DONE;\n",
        )
        self.assertEqual(
            form.errors["new_project_url"],
            [
                "Informe a URL para criar um projeto novo, "
                "ou escolha um projeto existente para as linhas sem github."
            ],
        )
