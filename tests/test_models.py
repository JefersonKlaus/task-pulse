from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from tasks.models import Project, Repository, Task


class RepositoryModelTests(TestCase):
    def test_repository_can_be_created_with_name_only(self):
        repository = Repository.objects.create(name="task-pulse")
        self.assertEqual(repository.name, "task-pulse")
        self.assertEqual(repository.description, "")
        self.assertIsNotNone(repository.created_at)

    def test_repository_accepts_optional_description(self):
        repository = Repository.objects.create(
            name="task-pulse",
            description="Sistema local de tarefas",
        )
        self.assertEqual(repository.description, "Sistema local de tarefas")

    def test_repository_string_representation_is_its_name(self):
        repository = Repository(name="task-pulse")
        self.assertEqual(str(repository), "task-pulse")

    def test_repository_ordering_is_alphabetical(self):
        Repository.objects.create(name="Zulu")
        Repository.objects.create(name="Alpha")
        Repository.objects.create(name="Mike")
        self.assertEqual(
            list(Repository.objects.values_list("name", flat=True)),
            ["Alpha", "Mike", "Zulu"],
        )

    def test_repository_name_is_required(self):
        repository = Repository(description="Sem nome")
        with self.assertRaises(ValidationError):
            repository.full_clean()

    def test_repository_description_may_be_blank(self):
        repository = Repository(name="Repo")
        repository.full_clean()
        self.assertEqual(repository.description, "")

    def test_repository_created_at_is_populated_on_save(self):
        repository = Repository.objects.create(name="Repo")
        self.assertIsInstance(repository.created_at, datetime)

    def test_repository_created_at_does_not_change_on_update(self):
        repository = Repository.objects.create(name="Repo")
        created_at = repository.created_at
        repository.name = "Repo atualizado"
        repository.save()
        repository.refresh_from_db()
        self.assertEqual(repository.created_at, created_at)

    def test_repository_can_have_multiple_projects(self):
        repository = Repository.objects.create(name="Repo")
        Project.objects.create(repository=repository, name="Projeto A")
        Project.objects.create(repository=repository, name="Projeto B")
        self.assertEqual(repository.projects.count(), 2)

    def test_repository_deletion_cascades_to_projects(self):
        repository = Repository.objects.create(name="Repo")
        project = Project.objects.create(repository=repository, name="Projeto")
        repository.delete()
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())

    def test_repository_name_maximum_length(self):
        repository = Repository(name="x" * 255)
        repository.full_clean()
        self.assertEqual(len(repository.name), 255)

    def test_repository_name_rejects_more_than_maximum_length(self):
        repository = Repository(name="x" * 256)
        with self.assertRaises(ValidationError):
            repository.full_clean()

    def test_repository_description_preserves_multiline_text(self):
        description = "Linha 1\nLinha 2"
        repository = Repository.objects.create(
            name="Repo",
            description=description,
        )
        self.assertEqual(repository.description, description)


class ProjectModelTests(TestCase):
    def setUp(self):
        self.repository = Repository.objects.create(name="Repo principal")

    def test_project_requires_repository(self):
        project = Project(name="Projeto sem repo")
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_project_requires_name(self):
        project = Project(repository=self.repository)
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_project_string_representation_is_its_name(self):
        project = Project(repository=self.repository, name="Portal")
        self.assertEqual(str(project), "Portal")

    def test_project_is_related_to_repository(self):
        project = Project.objects.create(
            repository=self.repository,
            name="Portal",
        )
        self.assertEqual(project.repository, self.repository)
        self.assertIn(project, self.repository.projects.all())

    def test_project_ordering_is_alphabetical(self):
        Project.objects.create(repository=self.repository, name="Zulu")
        Project.objects.create(repository=self.repository, name="Alpha")
        self.assertEqual(
            list(Project.objects.values_list("name", flat=True)),
            ["Alpha", "Zulu"],
        )

    def test_project_created_at_is_set_automatically(self):
        project = Project.objects.create(
            repository=self.repository,
            name="Portal",
        )
        self.assertIsNotNone(project.created_at)

    def test_project_name_accepts_maximum_length(self):
        project = Project(
            repository=self.repository,
            name="x" * 255,
        )
        project.full_clean()

    def test_project_name_rejects_excessive_length(self):
        project = Project(
            repository=self.repository,
            name="x" * 256,
        )
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_deleting_project_cascades_to_tasks(self):
        project = Project.objects.create(
            repository=self.repository,
            name="Portal",
        )
        task = Task.objects.create(
            project=project,
            nickname="Criar tela",
            time_spent=Decimal("2.50"),
            language="Python",
            date=date(2026, 1, 10),
        )
        project.delete()
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_project_can_have_many_tasks(self):
        project = Project.objects.create(
            repository=self.repository,
            name="Portal",
        )
        for index in range(3):
            Task.objects.create(
                project=project,
                nickname=f"Tarefa {index}",
                time_spent=Decimal("1.00"),
                language="Python",
                date=date(2026, 1, index + 1),
            )
        self.assertEqual(project.tasks.count(), 3)

    def test_projects_from_different_repositories_are_independent(self):
        other_repository = Repository.objects.create(name="Outro repo")
        first = Project.objects.create(
            repository=self.repository,
            name="Mesmo nome",
        )
        second = Project.objects.create(
            repository=other_repository,
            name="Mesmo nome",
        )
        self.assertNotEqual(first.repository, second.repository)
        self.assertEqual(self.repository.projects.count(), 1)
        self.assertEqual(other_repository.projects.count(), 1)


class TaskModelTests(TestCase):
    def setUp(self):
        repository = Repository.objects.create(name="Repo")
        self.project = Project.objects.create(
            repository=repository,
            name="Projeto",
        )

    def make_task(self, **overrides):
        values = {
            "project": self.project,
            "nickname": "Implementar recurso",
            "time_spent": Decimal("3.50"),
            "language": "Python",
            "date": date(2026, 2, 20),
        }
        values.update(overrides)
        return Task.objects.create(**values)

    def test_task_string_representation_is_nickname(self):
        task = self.make_task()
        self.assertEqual(str(task), "Implementar recurso")

    def test_task_default_status_is_review(self):
        task = self.make_task()
        self.assertEqual(task.status, Task.Status.REVIEW)

    def test_status_has_exactly_required_values(self):
        values = [value for value, label in Task.Status.choices]
        self.assertEqual(values, ["REJECTED", "DONE", "REVIEW"])

    def test_status_labels_are_expected(self):
        labels = [label for value, label in Task.Status.choices]
        self.assertEqual(labels, ["Rejeitado", "Done", "Review"])

    def test_rejected_status_can_be_saved(self):
        task = self.make_task(status=Task.Status.REJECTED)
        self.assertEqual(task.status, "REJECTED")

    def test_done_status_can_be_saved(self):
        task = self.make_task(status=Task.Status.DONE)
        self.assertEqual(task.status, "DONE")

    def test_review_status_can_be_saved(self):
        task = self.make_task(status=Task.Status.REVIEW)
        self.assertEqual(task.status, "REVIEW")

    def test_invalid_status_fails_model_validation(self):
        task = Task(
            project=self.project,
            nickname="Tarefa",
            time_spent=Decimal("1.00"),
            language="Python",
            date=date.today(),
            status="OPEN",
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_requires_project(self):
        task = Task(
            nickname="Tarefa",
            time_spent=Decimal("1.00"),
            language="Python",
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_requires_nickname(self):
        task = Task(
            project=self.project,
            time_spent=Decimal("1.00"),
            language="Python",
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_requires_date(self):
        task = Task(
            project=self.project,
            nickname="Tarefa",
            time_spent=Decimal("1.00"),
            language="Python",
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_requires_language(self):
        task = Task(
            project=self.project,
            nickname="Tarefa",
            time_spent=Decimal("1.00"),
            language="",
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_accepts_decimal_hours(self):
        task = self.make_task(time_spent=Decimal("2.75"))
        self.assertEqual(task.time_spent, Decimal("2.75"))

    def test_task_accepts_zero_hours(self):
        task = self.make_task(time_spent=Decimal("0.00"))
        self.assertEqual(task.time_spent, Decimal("0.00"))

    def test_task_rejects_negative_hours(self):
        task = Task(
            project=self.project,
            nickname="Tarefa",
            time_spent=Decimal("-1.00"),
            language="Python",
            date=date.today(),
        )
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_orders_by_date_descending_then_nickname(self):
        self.make_task(
            nickname="Antiga",
            date=date(2026, 1, 1),
        )
        self.make_task(
            nickname="Recente",
            date=date(2026, 3, 1),
        )
        names = list(
            Task.objects.values_list("nickname", flat=True)
        )
        self.assertEqual(names, ["Recente", "Antiga"])

    def test_task_accepts_optional_external_id(self):
        task = self.make_task(external_id="")
        self.assertEqual(task.external_id, "")

    def test_task_stores_external_id(self):
        task = self.make_task(external_id="TICKET-42")
        self.assertEqual(task.external_id, "TICKET-42")

    def test_task_language_maximum_length(self):
        task = self.make_task(language="x" * 100)
        task.full_clean()

    def test_task_language_rejects_excessive_length(self):
        task = self.make_task(language="x" * 101)
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_task_related_manager_returns_project_tasks(self):
        task = self.make_task()
        self.assertEqual(list(self.project.tasks.all()), [task])

    def test_task_deletion_does_not_delete_project(self):
        task = self.make_task()
        task.delete()
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_task_date_is_persisted_without_timezone_conversion(self):
        selected_date = date(2026, 11, 16)
        task = self.make_task(date=selected_date)
        task.refresh_from_db()
        self.assertEqual(task.date, selected_date)
