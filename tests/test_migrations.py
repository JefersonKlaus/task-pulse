from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from src.models import Project, Task


class MigrationTests(TestCase):
    def test_models_have_no_changes_missing_a_migration(self):
        try:
            call_command(
                "makemigrations",
                "tasks",
                "--check",
                "--dry-run",
                stdout=StringIO(),
                stderr=StringIO(),
            )
        except SystemExit:
            self.fail("Model changes detected: run `python manage.py makemigrations`.")

    def test_table_names_stay_the_same(self):
        # The app is the "src" package but keeps the label "tasks", so
        # databases created before the code moved keep working.
        self.assertEqual(
            (Project._meta.db_table, Task._meta.db_table),
            ("tasks_project", "tasks_task"),
        )
