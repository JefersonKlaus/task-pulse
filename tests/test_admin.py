from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tests.factories import create_task


class AdminPagesTests(TestCase):
    """The admin lists render (a broken column would raise an error)."""

    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@a.com", "x"))
        create_task(name="Tela de login", external_id="TP-1", minutes_spent=210)

    def test_task_list_shows_hours(self):
        response = self.client.get(reverse("admin:tasks_task_changelist"))
        self.assertContains(response, "Tela de login")
        self.assertContains(response, "3.50h")

    def test_project_list(self):
        response = self.client.get(reverse("admin:tasks_project_changelist"))
        self.assertEqual(response.status_code, 200)
