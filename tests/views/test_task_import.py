from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from src.models import Project, Task
from tests.factories import create_project, create_provider, create_task
from tests.integrations.test_tasks_csv import SAMPLE_FILE

CSV = (
    b"date;id;time;desc;status\n"
    b"16/11/2026;TP-101;3,8;Tela de login;DONE\n"
    b"17/11/2026;TP-102;1,5;API de tarefas;DOING\n"
)


class TaskImportViewTests(TestCase):
    url = reverse("tasks:task_import")

    def setUp(self):
        # The company of the projects an import creates.
        self.provider = create_provider()

    def post(self, data, content=CSV):
        upload = SimpleUploadedFile("tarefas.csv", content, content_type="text/csv")
        data = {"provider": self.provider.pk, **data, "file": upload}
        return self.client.post(self.url, data, follow=True)

    def test_page_explains_the_format_and_preselects_the_project(self):
        project = create_project(name="Portal do Cliente")
        response = self.client.get(self.url, {"projeto": project.pk})
        self.assertContains(response, "date;id;time;desc;status;github")
        # The chosen project is only for the lines without github.
        self.assertContains(response, "<legend>Projeto das linhas sem github</legend>")
        self.assertContains(response, f'<option value="{project.pk}" selected>')

    def test_imports_into_an_existing_project(self):
        project = create_project(name="Portal do Cliente")
        response = self.post({"project": project.pk})
        self.assertRedirects(
            response, reverse("tasks:project_detail", args=[project.pk])
        )
        self.assertEqual(project.tasks.count(), 2)
        self.assertContains(
            response,
            "2 linha(s) processada(s) em “Portal do Cliente”: "
            "2 tarefa(s) criada(s), 0 ignorada(s) (id já existente no projeto).",
        )

    def test_imports_into_a_new_project(self):
        self.post({"new_project_url": "https://github.com/acme/portal.git"})
        project = Project.objects.get()
        self.assertEqual((project.name, project.tasks.count()), ("portal", 2))

    def test_reimport_skips_existing_ids(self):
        project = create_project()
        existing = create_task(
            project, external_id="TP-101", name="Antiga", minutes_spent=10
        )
        response = self.post({"project": project.pk})
        existing.refresh_from_db()
        self.assertEqual((existing.name, existing.minutes_spent), ("Antiga", 10))
        self.assertContains(response, "1 tarefa(s) criada(s), 1 ignorada(s)")

    def test_a_file_with_errors_imports_nothing(self):
        bad = (
            b"date;id;time;desc;status\n31/02/2026;A;1;T;DONE\n16/11/2026;B;1;T;DONE\n"
        )
        response = self.post({"new_project_url": "https://github.com/acme/x.git"}, bad)
        self.assertContains(response, "Linha 2: data inválida “31/02/2026”")
        self.assertEqual((Project.objects.count(), Task.objects.count()), (0, 0))

    def test_the_sample_file_imports_and_reimports_nothing(self):
        sample = SAMPLE_FILE.read_bytes()
        self.post({"new_project_url": "https://github.com/acme/portal.git"}, sample)
        self.assertEqual(
            {project.name: project.tasks.count() for project in Project.objects.all()},
            {"portal": 29, "cotacao-api": 4, "graficos": 2},
        )
        portal = Project.objects.get(name="portal")
        response = self.post({"project": portal.pk}, sample)
        self.assertContains(response, "35 linha(s) processada(s) em 3 projetos")
        self.assertEqual(Task.objects.count(), 35)

    def test_each_row_goes_to_the_project_of_its_github_repository(self):
        portal = create_project(name="Portal", url="https://github.com/acme/portal")
        response = self.post(
            {},  # no project chosen: every row has github
            b"date;id;time;desc;status;github\n"
            b"16/11/2026;12;1;Login;DONE;acme/portal\n"
            b"16/11/2026;12;2;API;DONE;acme/api\n"
            b"17/11/2026;13;1;Logout;DOING;git@github.com:acme/portal.git\n",
        )
        self.assertRedirects(response, reverse("tasks:project_list"))
        api = Project.objects.get(name="api")
        self.assertEqual(
            (portal.tasks.count(), api.tasks.count(), api.url),
            (2, 1, "https://github.com/acme/api"),
        )
        self.assertContains(
            response,
            "3 linha(s) processada(s) em 2 projetos — "
            "“Portal”: 2 tarefa(s) criada(s), 0 ignorada(s); "
            "“api” (projeto novo): 1 tarefa(s) criada(s), 0 ignorada(s) "
            "(id já existente no projeto).",
        )

    def test_one_github_project_opens_its_page(self):
        self.post(
            {},
            b"date;id;time;desc;status;github\n16/11/2026;1;1;Login;DONE;acme/api\n",
        )
        api = Project.objects.get()
        response = self.post(
            {},
            b"date;id;time;desc;status;github\n16/11/2026;1;1;Login;DONE;acme/api\n",
        )
        self.assertRedirects(response, reverse("tasks:project_detail", args=[api.pk]))
        self.assertContains(
            response, "em “api”: 0 tarefa(s) criada(s), 1 ignorada(s)"
        )
