from django.apps import apps
from django.test import SimpleTestCase

from tasks.apps import TasksConfig


class TasksConfigTests(SimpleTestCase):
    def test_app_config_name(self):
        self.assertEqual(TasksConfig.name, "tasks")

    def test_app_config_default_auto_field(self):
        self.assertEqual(
            TasksConfig.default_auto_field,
            "django.db.models.BigAutoField",
        )

    def test_tasks_app_is_installed(self):
        config = apps.get_app_config("tasks")
        self.assertEqual(config.name, "tasks")

    def test_tasks_app_has_models_module(self):
        config = apps.get_app_config("tasks")
        self.assertEqual(config.models_module.__name__, "tasks.models")

    def test_tasks_app_has_admin_module(self):
        config = apps.get_app_config("tasks")
        self.assertEqual(config.module.__name__, "tasks")
