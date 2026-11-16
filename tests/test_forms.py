from datetime import date
from decimal import Decimal

from django.test import TestCase

from tasks.forms import ProjectForm, TaskForm
from tasks.models import Project, Repository, Task


class ProjectFormTests(TestCase):
    def setUp(self):
        self.repository = Repository.objects.create(name="Repo")

    def test_form_has_only_repository_and_name_fields(self):
        self.assertEqual(
            list(ProjectForm().fields),
            ["repository", "name"],
        )

    def test_form_is_valid_with_required_values(self):
        form = ProjectForm(
            data={
                "repository": self.repository.pk,
                "name": "Novo projeto",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_saves_project_with_selected_repository(self):
        form = ProjectForm(
            data={
                "repository": self.repository.pk,
                "name": "Novo projeto",
            }
        )
        project = form.save()
        self.assertEqual(project.repository, self.repository)
        self.assertEqual(project.name, "Novo projeto")

    def test_form_rejects_missing_repository(self):
        form = ProjectForm(data={"name": "Sem repo"})
        self.assertFalse(form.is_valid())
        self.assertIn("repository", form.errors)

    def test_form_rejects_missing_name(self):
        form = ProjectForm(data={"repository": self.repository.pk})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_form_rejects_invalid_repository_id(self):
        form = ProjectForm(
            data={"repository": 99999, "name": "Projeto"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("repository", form.errors)

    def test_form_uses_portuguese_labels(self):
        form = ProjectForm()
        self.assertEqual(form.fields["repository"].label, "Repositório")
        self.assertEqual(form.fields["name"].label, "Nome do projeto")

    def test_name_widget_has_placeholder(self):
        widget = ProjectForm().fields["name"].widget
        self.assertEqual(widget.attrs["placeholder"], "Ex.: Portal web")

    def test_form_accepts_unicode_project_name(self):
        form = ProjectForm(
            data={
                "repository": self.repository.pk,
                "name": "Gestão de tarefas",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_name_above_maximum_length(self):
        form = ProjectForm(
            data={
                "repository": self.repository.pk,
                "name": "x" * 256,
            }
        )
        self.assertFalse(form.is_valid())

    def test_repository_queryset_contains_created_repository(self):
        form = ProjectForm()
        self.assertIn(
            self.repository,
            form.fields["repository"].queryset,
        )

    def test_repository_queryset_is_not_hardcoded(self):
        other = Repository.objects.create(name="Outro")
        names = list(
            ProjectForm().fields["repository"].queryset.values_list(
                "name",
                flat=True,
            )
        )
        self.assertEqual(names, ["Outro", "Repo"])
        self.assertIn(other.name, names)


class TaskFormTests(TestCase):
    def test_form_has_only_user_facing_task_fields(self):
        self.assertEqual(
            list(TaskForm().fields),
            ["nickname", "time_spent", "language", "date"],
        )

    def valid_data(self):
        return {
            "nickname": "Implementar tela",
            "time_spent": "2.50",
            "language": "Python",
            "date": "2026-11-16",
        }

    def test_form_is_valid_with_all_values(self):
        form = TaskForm(data=self.valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_creates_unsaved_task_without_project(self):
        form = TaskForm(data=self.valid_data())
        task = form.save(commit=False)
        self.assertIsNone(task.project_id)
        self.assertEqual(task.nickname, "Implementar tela")
        self.assertEqual(task.time_spent, Decimal("2.50"))

    def test_form_rejects_missing_nickname(self):
        data = self.valid_data()
        del data["nickname"]
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("nickname", form.errors)

    def test_form_rejects_missing_time(self):
        data = self.valid_data()
        del data["time_spent"]
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("time_spent", form.errors)

    def test_form_rejects_missing_language(self):
        data = self.valid_data()
        del data["language"]
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("language", form.errors)

    def test_form_rejects_missing_date(self):
        data = self.valid_data()
        del data["date"]
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_form_rejects_invalid_date(self):
        data = self.valid_data()
        data["date"] = "not-a-date"
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_form_rejects_negative_time(self):
        data = self.valid_data()
        data["time_spent"] = "-1"
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("time_spent", form.errors)

    def test_form_accepts_quarter_hour(self):
        data = self.valid_data()
        data["time_spent"] = "0.25"
        form = TaskForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["time_spent"], Decimal("0.25"))

    def test_form_accepts_zero_time(self):
        data = self.valid_data()
        data["time_spent"] = "0"
        form = TaskForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_uses_portuguese_labels(self):
        form = TaskForm()
        labels = {
            name: field.label
            for name, field in form.fields.items()
        }
        self.assertEqual(
            labels,
            {
                "nickname": "Nome da tarefa",
                "time_spent": "Horas",
                "language": "Linguagem",
                "date": "Data",
            },
        )

    def test_time_widget_has_quarter_step(self):
        widget = TaskForm().fields["time_spent"].widget
        self.assertEqual(widget.attrs["step"], "0.25")

    def test_time_widget_has_zero_minimum(self):
        widget = TaskForm().fields["time_spent"].widget
        self.assertEqual(widget.attrs["min"], "0")

    def test_time_widget_has_example_placeholder(self):
        widget = TaskForm().fields["time_spent"].widget
        self.assertEqual(widget.attrs["placeholder"], "Ex.: 2.5")

    def test_language_widget_has_example_placeholder(self):
        widget = TaskForm().fields["language"].widget
        self.assertEqual(widget.attrs["placeholder"], "Ex.: Python")

    def test_date_widget_uses_html_date_input(self):
        widget = TaskForm().fields["date"].widget
        self.assertEqual(widget.input_type, "date")

    def test_form_parses_date_as_date_instance(self):
        form = TaskForm(data=self.valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["date"],
            date(2026, 11, 16),
        )

    def test_form_rejects_time_with_too_many_decimal_places(self):
        data = self.valid_data()
        data["time_spent"] = "1.999"
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())

    def test_form_rejects_time_above_maximum_digits(self):
        data = self.valid_data()
        data["time_spent"] = "100000.00"
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())

    def test_form_accepts_unicode_language(self):
        data = self.valid_data()
        data["language"] = "C#"
        form = TaskForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_accepts_long_but_valid_nickname(self):
        data = self.valid_data()
        data["nickname"] = "x" * 255
        form = TaskForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_nickname_above_maximum_length(self):
        data = self.valid_data()
        data["nickname"] = "x" * 256
        form = TaskForm(data=data)
        self.assertFalse(form.is_valid())
