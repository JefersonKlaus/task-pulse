from django.test import SimpleTestCase

from tasks.models import Project, Repository, Task


class ModelMetadataTests(SimpleTestCase):
    def test_repository_verbose_name(self):
        self.assertEqual(Repository._meta.verbose_name, "repositório")

    def test_repository_plural_verbose_name(self):
        self.assertEqual(
            Repository._meta.verbose_name_plural,
            "repositórios",
        )

    def test_repository_ordering(self):
        self.assertEqual(Repository._meta.ordering, ["name"])

    def test_repository_name_field_is_char_field(self):
        self.assertEqual(Repository._meta.get_field("name").__class__.__name__, "CharField")

    def test_repository_description_field_is_text_field(self):
        self.assertEqual(
            Repository._meta.get_field("description").__class__.__name__,
            "TextField",
        )

    def test_repository_created_at_is_auto_now_add(self):
        self.assertTrue(
            Repository._meta.get_field("created_at").auto_now_add
        )

    def test_project_verbose_name(self):
        self.assertEqual(Project._meta.verbose_name, "projeto")

    def test_project_plural_verbose_name(self):
        self.assertEqual(Project._meta.verbose_name_plural, "projetos")

    def test_project_repository_has_expected_related_name(self):
        field = Project._meta.get_field("repository")
        self.assertEqual(field.remote_field.related_name, "projects")

    def test_project_name_is_char_field(self):
        self.assertEqual(
            Project._meta.get_field("name").__class__.__name__,
            "CharField",
        )

    def test_task_verbose_name(self):
        self.assertEqual(Task._meta.verbose_name, "tarefa")

    def test_task_plural_verbose_name(self):
        self.assertEqual(Task._meta.verbose_name_plural, "tarefas")

    def test_task_project_has_expected_related_name(self):
        field = Task._meta.get_field("project")
        self.assertEqual(field.remote_field.related_name, "tasks")

    def test_task_time_spent_is_decimal_field(self):
        field = Task._meta.get_field("time_spent")
        self.assertEqual(field.__class__.__name__, "DecimalField")
        self.assertEqual(field.max_digits, 6)
        self.assertEqual(field.decimal_places, 2)

    def test_task_date_is_date_field(self):
        self.assertEqual(
            Task._meta.get_field("date").__class__.__name__,
            "DateField",
        )

    def test_task_language_is_char_field(self):
        self.assertEqual(
            Task._meta.get_field("language").__class__.__name__,
            "CharField",
        )

    def test_task_status_has_expected_max_length(self):
        self.assertEqual(Task._meta.get_field("status").max_length, 8)

    def test_task_status_default_is_review(self):
        self.assertEqual(
            Task._meta.get_field("status").default,
            Task.Status.REVIEW,
        )

    def test_task_external_id_is_optional(self):
        field = Task._meta.get_field("external_id")
        self.assertTrue(field.blank)

    def test_task_external_id_is_char_field(self):
        self.assertEqual(
            Task._meta.get_field("external_id").__class__.__name__,
            "CharField",
        )

    def test_task_ordering(self):
        self.assertEqual(
            Task._meta.ordering,
            ["-date", "nickname"],
        )
