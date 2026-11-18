from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from src.integrations.tasks_csv import ImportedRow
from src.models import Project, Task
from src.services.task_import import (
    ImportResult,
    NewProject,
    ProjectImport,
    import_rows,
    import_tasks,
)
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
        (imported,) = import_tasks([row()], self.project)
        task = Task.objects.get()
        self.assertEqual(
            imported, ProjectImport(self.project, ImportResult(1, 0), new=False)
        )
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

    def test_desc_that_fits_the_name_is_kept_whole(self):
        import_tasks([row(desc="x" * 255)], self.project)
        task = Task.objects.get()
        self.assertEqual((task.name, task.description), ("x" * 255, ""))

    def test_existing_ids_are_skipped_and_left_untouched(self):
        existing = create_task(
            self.project, external_id="TP-1", name="Antiga", minutes_spent=30
        )
        (imported,) = import_tasks([row("TP-1"), row("TP-2")], self.project)
        existing.refresh_from_db()
        self.assertEqual(imported.result, ImportResult(created=1, skipped=1))
        self.assertEqual((existing.name, existing.minutes_spent), ("Antiga", 30))

    def test_ids_are_only_matched_inside_the_project(self):
        create_task(create_project(name="Outro"), external_id="TP-1")
        (imported,) = import_tasks([row("TP-1")], self.project)
        self.assertEqual(imported.result.created, 1)


class ImportTasksIntoNewProjectTests(TestCase):
    def test_creates_the_project_named_after_its_repository(self):
        (imported,) = import_tasks(
            [row()], NewProject(url="https://github.com/acme/portal.git")
        )
        project = imported.project
        self.assertEqual((project.name, project.tasks.count()), ("portal", 1))
        self.assertTrue(imported.new)

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


class ImportTasksByGithubTests(TestCase):
    """Rows with a github repository go to that repository's project."""

    def names(self, imports):
        return [(i.project.name, i.result.created, i.new) for i in imports]

    def test_creates_a_project_per_new_repository(self):
        imports = import_tasks(
            [
                row("1", github="https://github.com/acme/portal"),
                row("2", github="https://github.com/acme/api"),
                row("3", github="https://github.com/acme/portal"),
            ]
        )
        self.assertEqual(self.names(imports), [("portal", 2, True), ("api", 1, True)])
        self.assertEqual(
            Project.objects.get(name="portal").url, "https://github.com/acme/portal"
        )

    def test_uses_the_existing_project_however_its_url_is_written(self):
        existing = create_project(name="Portal", url="git@github.com:Acme/Portal.git")
        (imported,) = import_tasks([row(github="https://github.com/acme/portal")])
        self.assertEqual((imported.project, imported.new), (existing, False))
        self.assertEqual(Project.objects.count(), 1)

    def test_the_oldest_project_of_a_repository_wins(self):
        oldest = create_project(url="https://github.com/acme/portal")
        create_project(url="https://github.com/acme/portal.git")
        (imported,) = import_tasks([row(github="https://github.com/acme/portal")])
        self.assertEqual(imported.project, oldest)

    def test_rows_without_github_go_to_the_chosen_project(self):
        chosen = create_project(name="Escolhido", url="https://github.com/acme/x")
        imports = import_tasks(
            [row("1"), row("2", github="https://github.com/acme/api")], chosen
        )
        self.assertEqual(
            self.names(imports), [("Escolhido", 1, False), ("api", 1, True)]
        )

    def test_a_new_chosen_project_is_only_created_when_needed(self):
        imports = import_tasks(
            [row(github="https://github.com/acme/api")],
            NewProject(url="https://github.com/acme/unused"),
        )
        self.assertEqual(self.names(imports), [("api", 1, True)])
        self.assertFalse(Project.objects.filter(name="unused").exists())

    def test_rows_naming_the_new_chosen_project_join_it(self):
        imports = import_tasks(
            [row("1"), row("2", github="https://github.com/acme/portal.git")],
            NewProject(url="https://github.com/acme/portal"),
        )
        self.assertEqual(self.names(imports), [("portal", 2, True)])
        self.assertEqual(Project.objects.count(), 1)

    def test_ids_are_skipped_per_project(self):
        portal = create_project(url="https://github.com/acme/portal")
        create_task(portal, external_id="12")
        imports = import_tasks(
            [
                row("12", github="https://github.com/acme/portal"),  # known
                row("12", github="https://github.com/acme/api"),  # new there
            ]
        )
        self.assertEqual(
            [(i.project.name, i.result) for i in imports],
            [("Projeto", ImportResult(0, 1)), ("api", ImportResult(1, 0))],
        )

    def test_nothing_is_kept_when_a_later_project_fails(self):
        real_import_rows = import_rows

        def fail_in_the_second_project(project, rows):
            if project.name == "api":
                raise RuntimeError
            return real_import_rows(project, rows)

        with mock.patch(
            "src.services.task_import.import_rows",
            side_effect=fail_in_the_second_project,
        ):
            with self.assertRaises(RuntimeError):
                import_tasks(
                    [
                        row("1", github="https://github.com/acme/portal"),
                        row("2", github="https://github.com/acme/api"),
                    ]
                )
        self.assertEqual((Project.objects.count(), Task.objects.count()), (0, 0))
