from django.test import TestCase

from src.models import Task
from tests.factories import create_project, create_task

URL = "https://github.com/acme/task-pulse.git"


class ProjectDefaultNameTests(TestCase):
    """A project without a name is named after its repository."""

    def test_blank_name_comes_from_the_url(self):
        for name in ("", "   "):
            with self.subTest(name=repr(name)):
                project = create_project(url=URL, name=name)
                project.refresh_from_db()
                self.assertEqual(project.name, "task-pulse")

    def test_given_name_is_kept(self):
        self.assertEqual(create_project(url=URL, name="Meu").name, "Meu")

    def test_name_is_kept_when_the_url_changes(self):
        project = create_project(url=URL, name="")
        project.url = "https://github.com/acme/outro"
        project.save()
        self.assertEqual(project.name, "task-pulse")


class ProjectDeletionTests(TestCase):
    def test_deleting_a_project_deletes_its_tasks(self):
        project = create_project()
        create_task(project)
        project.delete()
        self.assertFalse(Task.objects.exists())
