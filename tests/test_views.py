from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from tasks.models import Project, Repository, Task


class ViewTestDataMixin:
    def create_repository(self, name="Repo"):
        return Repository.objects.create(name=name)

    def create_project(self, name="Projeto", repository=None):
        repository = repository or self.create_repository()
        return Project.objects.create(
            repository=repository,
            name=name,
        )

    def create_task(self, project, nickname="Tarefa", **values):
        defaults = {
            "time_spent": Decimal("1.50"),
            "language": "Python",
            "date": date(2026, 11, 16),
        }
        defaults.update(values)
        return Task.objects.create(
            project=project,
            nickname=nickname,
            **defaults,
        )


class ProjectListViewTests(ViewTestDataMixin, TestCase):
    def test_list_url_returns_success(self):
        response = self.client.get(reverse("tasks:project_list"))
        self.assertEqual(response.status_code, 200)

    def test_list_uses_expected_template(self):
        response = self.client.get(reverse("tasks:project_list"))
        self.assertTemplateUsed(response, "tasks/project_list.html")

    def test_list_contains_projects(self):
        project = self.create_project()
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, project.name)
        self.assertContains(response, project.repository.name)

    def test_list_contains_project_link(self):
        project = self.create_project()
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(
            response,
            reverse("tasks:project_detail", args=[project.pk]),
        )

    def test_empty_list_shows_empty_message(self):
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, "Nenhum projeto cadastrado.")

    def test_empty_list_has_create_link(self):
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(
            response,
            reverse("tasks:project_create"),
        )

    def test_list_shows_task_count(self):
        project = self.create_project()
        self.create_task(project)
        self.create_task(project, nickname="Outra")
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, "2 tarefas")

    def test_list_orders_projects_by_name(self):
        self.create_project(name="Zeta")
        self.create_project(name="Alpha")
        response = self.client.get(reverse("tasks:project_list"))
        self.assertLess(
            response.content.index(b"Alpha"),
            response.content.index(b"Zeta"),
        )

    def test_list_has_new_project_button(self):
        response = self.client.get(reverse("tasks:project_list"))
        self.assertContains(response, "Novo projeto")

    def test_list_uses_get_method(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class ProjectCreateViewTests(ViewTestDataMixin, TestCase):
    def setUp(self):
        self.repository = self.create_repository()
        self.url = reverse("tasks:project_create")

    def test_create_page_returns_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_create_page_uses_form_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "tasks/project_form.html")

    def test_create_page_contains_form_fields(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="repository"')
        self.assertContains(response, 'name="name"')

    def test_valid_post_creates_project(self):
        response = self.client.post(
            self.url,
            {
                "repository": self.repository.pk,
                "name": "Novo projeto",
            },
        )
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(Project.objects.first().name, "Novo projeto")
        self.assertEqual(response.status_code, 302)

    def test_valid_post_redirects_to_detail(self):
        response = self.client.post(
            self.url,
            {
                "repository": self.repository.pk,
                "name": "Novo projeto",
            },
        )
        project = Project.objects.get()
        self.assertRedirects(
            response,
            reverse("tasks:project_detail", args=[project.pk]),
        )

    def test_invalid_post_does_not_create_project(self):
        response = self.client.post(
            self.url,
            {"repository": self.repository.pk, "name": ""},
        )
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_invalid_post_renders_errors(self):
        response = self.client.post(
            self.url,
            {"repository": self.repository.pk, "name": ""},
        )
        self.assertContains(response, "Este campo é obrigatório.")

    def test_post_with_unknown_repository_is_invalid(self):
        response = self.client.post(
            self.url,
            {"repository": 99999, "name": "Projeto"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Project.objects.count(), 0)

    def test_post_with_missing_repository_is_invalid(self):
        response = self.client.post(
            self.url,
            {"name": "Projeto"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Project.objects.count(), 0)

    def test_create_does_not_accept_get_parameters_as_project(self):
        response = self.client.get(
            self.url,
            {"repository": self.repository.pk, "name": "Ignorado"},
        )
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(response.status_code, 200)


class ProjectDetailViewTests(ViewTestDataMixin, TestCase):
    def setUp(self):
        self.project = self.create_project()
        self.url = reverse(
            "tasks:project_detail",
            args=[self.project.pk],
        )

    def valid_task_data(self, nickname="Nova tarefa"):
        return {
            "nickname": nickname,
            "time_spent": "2.25",
            "language": "Python",
            "date": "2026-11-16",
        }

    def test_detail_page_returns_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_detail_uses_expected_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "tasks/project_detail.html")

    def test_detail_contains_project_name(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.project.name)

    def test_detail_contains_repository_name(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.project.repository.name)

    def test_detail_contains_task_form(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="nickname"')
        self.assertContains(response, 'name="time_spent"')
        self.assertContains(response, 'name="language"')
        self.assertContains(response, 'name="date"')

    def test_detail_contains_existing_task(self):
        task = self.create_task(self.project)
        response = self.client.get(self.url)
        self.assertContains(response, task.nickname)
        self.assertContains(response, task.language)

    def test_detail_shows_empty_task_message(self):
        response = self.client.get(self.url)
        self.assertContains(
            response,
            "Ainda não há tarefas neste projeto.",
        )

    def test_valid_post_creates_task_for_project(self):
        response = self.client.post(
            self.url,
            self.valid_task_data(),
        )
        self.assertEqual(Task.objects.count(), 1)
        task = Task.objects.get()
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.time_spent, Decimal("2.25"))
        self.assertEqual(response.status_code, 302)

    def test_valid_post_redirects_to_same_detail(self):
        response = self.client.post(
            self.url,
            self.valid_task_data(),
        )
        self.assertRedirects(response, self.url)

    def test_valid_post_uses_default_review_status(self):
        self.client.post(self.url, self.valid_task_data())
        self.assertEqual(Task.objects.get().status, Task.Status.REVIEW)

    def test_invalid_post_does_not_create_task(self):
        data = self.valid_task_data()
        data["nickname"] = ""
        response = self.client.post(self.url, data)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_invalid_post_renders_task_errors(self):
        data = self.valid_task_data()
        data["date"] = "invalid"
        response = self.client.post(self.url, data)
        self.assertContains(response, "Informe uma data válida.")

    def test_multiple_valid_posts_create_multiple_tasks(self):
        self.client.post(self.url, self.valid_task_data("Primeira"))
        self.client.post(self.url, self.valid_task_data("Segunda"))
        self.assertEqual(self.project.tasks.count(), 2)

    def test_task_post_does_not_need_project_id_in_payload(self):
        response = self.client.post(
            self.url,
            self.valid_task_data("Sem projeto no payload"),
        )
        task = Task.objects.get()
        self.assertEqual(task.project, self.project)
        self.assertEqual(response.status_code, 302)

    def test_detail_returns_not_found_for_unknown_project(self):
        response = self.client.get(
            reverse("tasks:project_detail", args=[99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_post_unknown_project_returns_not_found(self):
        response = self.client.post(
            reverse("tasks:project_detail", args=[99999]),
            self.valid_task_data(),
        )
        self.assertEqual(response.status_code, 404)

    def test_detail_displays_hours_with_h_suffix(self):
        self.create_task(
            self.project,
            time_spent=Decimal("4.50"),
        )
        response = self.client.get(self.url)
        self.assertContains(response, "4,50h")

    def test_detail_displays_form_again_after_invalid_post(self):
        data = self.valid_task_data()
        data["language"] = ""
        response = self.client.post(self.url, data)
        self.assertContains(response, 'name="nickname"')
        self.assertContains(response, "Este campo é obrigatório.")

    def test_detail_does_not_display_task_from_other_project(self):
        other = self.create_project(name="Outro")
        other_task = self.create_task(other, nickname="Somente outro")
        response = self.client.get(self.url)
        self.assertNotContains(response, other_task.nickname)

    def test_detail_shows_task_date_in_brazilian_format(self):
        self.create_task(
            self.project,
            date=date(2026, 1, 5),
        )
        response = self.client.get(self.url)
        self.assertContains(response, "05/01/2026")

    def test_detail_shows_task_language(self):
        self.create_task(self.project, language="JavaScript")
        response = self.client.get(self.url)
        self.assertContains(response, "JavaScript")

    def test_detail_links_back_to_project_list(self):
        response = self.client.get(self.url)
        self.assertContains(
            response,
            reverse("tasks:project_list"),
        )

    def test_detail_post_rejects_negative_hours(self):
        data = self.valid_task_data()
        data["time_spent"] = "-2"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.count(), 0)

    def test_detail_post_accepts_zero_hours(self):
        data = self.valid_task_data()
        data["time_spent"] = "0"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.get().time_spent, Decimal("0.00"))

    def test_detail_post_accepts_decimal_hours(self):
        data = self.valid_task_data()
        data["time_spent"] = "0.75"
        self.client.post(self.url, data)
        self.assertEqual(
            Task.objects.get().time_spent,
            Decimal("0.75"),
        )
