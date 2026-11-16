from django.test import SimpleTestCase
from django.urls import resolve, reverse

from tasks import views


class TaskUrlTests(SimpleTestCase):
    def test_project_list_reverse(self):
        self.assertEqual(reverse("tasks:project_list"), "/")

    def test_project_create_reverse(self):
        self.assertEqual(
            reverse("tasks:project_create"),
            "/projetos/novo/",
        )

    def test_project_detail_reverse(self):
        self.assertEqual(
            reverse("tasks:project_detail", args=[7]),
            "/projetos/7/",
        )

    def test_root_resolves_to_project_list(self):
        match = resolve("/")
        self.assertEqual(match.func, views.project_list)

    def test_create_resolves_to_project_create(self):
        match = resolve("/projetos/novo/")
        self.assertEqual(match.func, views.project_create)

    def test_detail_resolves_to_project_detail(self):
        match = resolve("/projetos/7/")
        self.assertEqual(match.func, views.project_detail)

    def test_detail_captures_integer_primary_key(self):
        match = resolve("/projetos/42/")
        self.assertEqual(match.kwargs["pk"], 42)

    def test_detail_does_not_match_non_integer_key(self):
        with self.assertRaisesResolver404():
            resolve("/projetos/abc/")

    class assertRaisesResolver404:
        def __enter__(self):
            from django.urls import Resolver404

            self.exception = Resolver404
            return self

        def __exit__(self, exception_type, exception, traceback):
            return exception_type is self.exception
