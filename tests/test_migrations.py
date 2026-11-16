from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.test import TransactionTestCase


class MigrationTests(TransactionTestCase):
    reset_sequences = True

    def test_latest_migration_is_applied(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(
            executor.loader.graph.leaf_nodes()
        )
        self.assertEqual(plan, [])

    def test_tasks_app_has_initial_migration(self):
        executor = MigrationExecutor(connection)
        self.assertIn(
            ("tasks", "0001_initial"),
            executor.loader.graph.nodes,
        )

    def test_migration_creates_expected_models(self):
        executor = MigrationExecutor(connection)
        state = executor.loader.project_state(
            executor.loader.graph.leaf_nodes()
        )
        self.assertIn(("tasks", "repository"), state.models)
        self.assertIn(("tasks", "project"), state.models)
        self.assertIn(("tasks", "task"), state.models)
