from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from src.integrations.tasks_csv import ImportedRow
from src.models import Project, Task
from src.services.task_import import ImportResult, NewProject, import_tasks
from tests.factories import create_project, create_task


def row(external_id="TP-1", **values):
    defaults = {
        "date": date(2026, 3, 2),
        "minutes": 228,
        "desc": "Tela de login",
        "status": "DONE",
    }
    defaults.update(values)
    return ImportedRow(external_id=external_id, **defaults)


class ImportTasksTests(TestCase):
    def setUp(self):
        self.project = create_project()

    def test_creates_a_task_from_each_row(self):
        _, result = import_tasks([row()], self.project)
        task = Task.objects.get()
        self.assertEqual(result, ImportResult(created=1, skipped=0))
        self.assertEqual(
            (
                task.project,
                task.external_id,
                task.name,
                task.minutes_spent,
                task.status,
            ),
            (self.project, "TP-1", "Tela de login", 228, "DONE"),
        )

    def test_the_date_is_the_start_and_also_the_finish_unless_doing(self):
        import_tasks([row("A", status="DONE"), row("B", status="DOING")], self.project)
        dates = {
            t.external_id: (t.started_on, t.finished_on) for t in Task.objects.all()
        }
        self.assertEqual(
            dates,
            {"A": (date(2026, 3, 2), date(2026, 3, 2)), "B": (date(2026, 3, 2), None)},
        )

    def test_long_desc_is_shortened_and_kept_as_description(self):
        import_tasks([row(desc="x" * 300)], self.project)
        task = Task.objects.get()
        self.assertEqual(
            (len(task.name), task.name[-1], task.description), (255, "…", "x" * 300)
        )

    def test_existing_ids_are_skipped_and_left_untouched(self):
        existing = create_task(
            self.project, external_id="TP-1", name="Antiga", minutes_spent=30
        )
        _, result = import_tasks([row("TP-1"), row("TP-2")], self.project)
        existing.refresh_from_db()
        self.assertEqual(result, ImportResult(created=1, skipped=1))
        self.assertEqual((existing.name, existing.minutes_spent), ("Antiga", 30))

    def test_ids_are_only_matched_inside_the_project(self):
        create_task(create_project(name="Outro"), external_id="TP-1")
        _, result = import_tasks([row("TP-1")], self.project)
        self.assertEqual(result.created, 1)


class ImportTasksIntoNewProjectTests(TestCase):
    def test_creates_the_project_named_after_its_repository(self):
        project, _ = import_tasks(
            [row()], NewProject(url="https://github.com/acme/portal.git")
        )
        self.assertEqual((project.name, project.tasks.count()), ("portal", 1))

    def test_nothing_is_kept_when_the_import_fails(self):
        with mock.patch(
            "src.services.task_import.import_rows", side_effect=RuntimeError
        ):
            with self.assertRaises(RuntimeError):
                import_tasks([row()], NewProject(url="https://github.com/acme/z.git"))
        self.assertEqual((Project.objects.count(), Task.objects.count()), (0, 0))

    def test_invalid_new_project_creates_nothing(self):
        with self.assertRaises(ValidationError):
            import_tasks([row()], NewProject(url=""))
        self.assertFalse(Project.objects.exists())
