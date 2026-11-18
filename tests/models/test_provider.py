from django.core.exceptions import ValidationError
from django.test import TestCase

from src.models import Project, Provider, Task
from tests.factories import create_project, create_provider, create_task


class ProviderTests(TestCase):
    def test_names_are_unique_whatever_the_case(self):
        create_provider("Etho")
        with self.assertRaises(ValidationError) as raised:
            Provider(name="ETHO").full_clean()
        self.assertEqual(
            raised.exception.messages, ["Já existe uma empresa com este nome."]
        )

    def test_deleting_a_company_keeps_its_projects_without_one(self):
        provider = create_provider()
        project = create_project(provider=provider)
        provider.delete()
        project.refresh_from_db()
        self.assertIsNone(project.provider)

    def test_projects_and_tasks_of_a_company(self):
        alignerr, etho = create_provider("Alignerr"), create_provider("Etho")
        mine = create_project(provider=alignerr)
        create_project(provider=etho)
        create_project()
        task = create_task(mine)
        create_task(create_project(provider=etho))
        self.assertEqual(list(Project.objects.of_provider(alignerr)), [mine])
        self.assertEqual(list(Task.objects.of_provider(alignerr)), [task])
        self.assertEqual(Project.objects.of_provider(None).count(), 4)
