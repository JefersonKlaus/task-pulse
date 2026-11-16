from django.contrib import admin
from django.test import TestCase

from tasks.admin import ProjectAdmin, RepositoryAdmin, TaskAdmin
from tasks.models import Project, Repository, Task


class AdminRegistrationTests(TestCase):
    def test_repository_is_registered(self):
        self.assertIsInstance(
            admin.site._registry[Repository],
            RepositoryAdmin,
        )

    def test_project_is_registered(self):
        self.assertIsInstance(
            admin.site._registry[Project],
            ProjectAdmin,
        )

    def test_task_is_registered(self):
        self.assertIsInstance(
            admin.site._registry[Task],
            TaskAdmin,
        )

    def test_repository_admin_list_display(self):
        self.assertEqual(
            RepositoryAdmin.list_display,
            ("name", "description", "created_at"),
        )

    def test_repository_admin_search_fields(self):
        self.assertEqual(
            RepositoryAdmin.search_fields,
            ("name", "description"),
        )

    def test_project_admin_list_display(self):
        self.assertEqual(
            ProjectAdmin.list_display,
            ("name", "repository", "created_at"),
        )

    def test_project_admin_list_filter(self):
        self.assertEqual(ProjectAdmin.list_filter, ("repository",))

    def test_project_admin_search_fields(self):
        self.assertEqual(
            ProjectAdmin.search_fields,
            ("name", "repository__name"),
        )

    def test_task_admin_list_display_contains_required_columns(self):
        self.assertEqual(
            TaskAdmin.list_display,
            (
                "nickname",
                "project",
                "external_id",
                "time_spent",
                "date",
                "status",
            ),
        )

    def test_task_admin_filters_by_status_repository_and_date(self):
        self.assertEqual(
            TaskAdmin.list_filter,
            ("status", "project__repository", "date"),
        )

    def test_task_admin_searches_nickname_and_external_id(self):
        self.assertEqual(
            TaskAdmin.search_fields,
            ("nickname", "external_id"),
        )

    def test_task_admin_uses_model_admin_base_class(self):
        self.assertTrue(issubclass(TaskAdmin, admin.ModelAdmin))

    def test_project_admin_uses_model_admin_base_class(self):
        self.assertTrue(issubclass(ProjectAdmin, admin.ModelAdmin))

    def test_repository_admin_uses_model_admin_base_class(self):
        self.assertTrue(issubclass(RepositoryAdmin, admin.ModelAdmin))
