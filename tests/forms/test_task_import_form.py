from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from src.forms import TaskImportForm
from src.services.task_import import NewProject
from tests.factories import create_project

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
        lines = b"".join(b"xx;ID%d;1;T;DONE\n" % n for n in range(25))
        errors = import_form({"project": create_project().pk}, HEADER + lines).errors[
            "file"
        ]
        self.assertEqual((len(errors), errors[-1]), (21, "… e mais 5 erros."))

    def test_rejects_files_over_the_size_limit(self):
        with mock.patch.object(TaskImportForm, "MAX_FILE_SIZE", 10):
            errors = import_form({"project": create_project().pk}).errors
        self.assertEqual(errors["file"], ["O arquivo tem mais de 2 MB."])

    def test_destination_is_the_selected_project(self):
        project = create_project()
        form = import_form(
            {"project": project.pk, "new_project_url": "https://x/ignored"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.destination(), project)

    def test_destination_is_a_new_project(self):
        form = import_form(
            {
                "new_project_url": "https://github.com/acme/x.git",
                "new_project_name": "Meu",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.destination(),
            NewProject(url="https://github.com/acme/x.git", name="Meu"),
        )
