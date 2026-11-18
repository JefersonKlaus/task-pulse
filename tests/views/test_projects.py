import re
from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from src.models import Project, Task
from tests.factories import create_project, create_provider, create_task
from tests.payloads import project_form_data, task_create_data


class ProjectListTests(TestCase):
    def test_lists_projects_with_url_and_task_count(self):
        project = create_project(
            name="Portal do Cliente", url="https://gitlab.com/acme/pc"
        )
        create_task(project)
        create_task(project)
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, "Portal do Cliente")
        self.assertContains(response, "https://gitlab.com/acme/pc")
        self.assertContains(response, "2 tarefas")
        self.assertContains(
            response, reverse("tasks:project_detail", args=[project.pk])
        )

    def test_one_row_per_project_in_name_order(self):
        for name in ("Portal", "API", "Mobile"):
            create_project(name=name)
        content = self.client.get(reverse("tasks:project_list")).content.decode()
        rows = re.findall(
            r'<li>\s*<a href=[^>]*>\s*<span class="project-info">\s*'
            r'<span class="project-title"><strong>(.*?)</strong>',
            content,
        )
        self.assertEqual(rows, ["API", "Mobile", "Portal"])

    def test_empty_list_invites_to_create_a_project(self):
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, "Nenhum projeto cadastrado.")
        self.assertContains(response, reverse("tasks:project_create"))


class ProjectCreateTests(TestCase):
    url = reverse("tasks:project_create")

    def test_creates_the_project_named_after_its_repository(self):
        provider = create_provider()
        response = self.client.post(
            self.url,
            project_form_data(
                url="git@github.com:acme/api.git", name="", provider=provider.pk
            ),
        )
        project = Project.objects.get()
        self.assertEqual(
            (project.url, project.name, project.provider),
            ("git@github.com:acme/api.git", "api", provider),
        )
        self.assertRedirects(
            response, reverse("tasks:project_detail", args=[project.pk])
        )

    def test_missing_url_shows_an_error_and_creates_nothing(self):
        response = self.client.post(self.url, project_form_data(url=""))
        self.assertContains(response, "Este campo é obrigatório.")
        self.assertFalse(Project.objects.exists())

    def test_a_project_needs_its_company(self):
        # The company pays for the project's tasks.
        response = self.client.post(self.url, project_form_data())
        self.assertContains(response, "Este campo é obrigatório.", count=1)
        self.assertFalse(Project.objects.exists())


class ProjectUpdateTests(TestCase):
    def setUp(self):
        self.project = create_project(
            name="Portal", url="https://github.com/acme/portal"
        )
        self.url = reverse("tasks:project_update", args=[self.project.pk])

    def test_edit_page_shows_the_current_values(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'value="Portal"')
        self.assertContains(response, 'value="https://github.com/acme/portal"')

    def test_updates_and_goes_back_to_the_project(self):
        provider = create_provider()
        response = self.client.post(
            self.url,
            project_form_data(
                url=self.project.url, name="Portal 2", provider=provider.pk
            ),
        )
        self.project.refresh_from_db()
        self.assertEqual(
            (self.project.name, self.project.provider), ("Portal 2", provider)
        )
        self.assertRedirects(
            response, reverse("tasks:project_detail", args=[self.project.pk])
        )

    def test_invalid_data_changes_nothing(self):
        self.client.post(self.url, project_form_data(url="", name="Outro"))
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Portal")

    def test_unknown_project_is_not_found(self):
        url = reverse("tasks:project_update", args=[99999])
        self.assertEqual(self.client.get(url).status_code, 404)


class ProjectDetailTests(TestCase):
    def setUp(self):
        # Distinctive values: generic ones ("Projeto") would also match the
        # static page text ("← Projetos").
        self.project = create_project(
            name="Portal do Cliente",
            url="https://github.com/acme/portal-cliente",
            description="Sistema de atendimento",
        )
        self.url = reverse("tasks:project_detail", args=[self.project.pk])

    def test_shows_the_project(self):
        response = self.client.get(self.url)
        self.assertContains(
            response,
            '<a href="https://github.com/acme/portal-cliente" '
            'rel="noopener noreferrer">https://github.com/acme/portal-cliente</a>',
            html=True,
        )
        self.assertContains(response, "Sistema de atendimento")

    def test_shows_each_task_with_status_dates_and_total(self):
        create_task(
            self.project,
            name="Tela de login",
            external_id="TP-1",
            status="DONE",
            started_on=date(2026, 1, 2),
            finished_on=date(2026, 1, 3),
            minutes_spent=210,
        )
        create_task(create_project(name="Outro"), name="Tarefa de outro projeto")
        response = self.client.get(self.url)
        for text in (
            "#TP-1",
            "Tela de login",
            "Início: 02/01/2026",
            "Término: 03/01/2026",
            "Total: 3.50h",
        ):
            with self.subTest(text=text):
                self.assertContains(response, text)
        self.assertContains(response, '<span class="status">Done</span>', html=True)
        self.assertNotContains(response, "Tarefa de outro projeto")

    def test_a_javascript_url_is_never_a_link(self):
        project = create_project(name="X", url="javascript:alert(1)")
        response = self.client.get(reverse("tasks:project_detail", args=[project.pk]))
        self.assertNotContains(response, 'href="javascript:')

    def test_creating_a_task(self):
        create_project(name="Outro")  # the task must go to the project in the URL
        response = self.client.post(
            self.url, task_create_data(name="Nova", status="DONE", minutes_spent="5:00")
        )
        task = Task.objects.get()
        self.assertRedirects(response, self.url)
        self.assertEqual(
            (task.project, task.status, task.started_on, task.minutes_spent),
            (self.project, "DOING", timezone.localdate(), 0),
        )

    def test_task_form_opens_only_when_needed(self):
        self.assertContains(self.client.get(self.url), '<details class="new-task">')
        response = self.client.post(self.url, task_create_data(name=""))
        self.assertContains(response, '<details class="new-task" open>')
        self.assertContains(response, "Este campo é obrigatório.")
        self.assertFalse(Task.objects.exists())

    def test_unknown_project_is_not_found(self):
        url = reverse("tasks:project_detail", args=[99999])
        self.assertEqual(self.client.get(url).status_code, 404)
