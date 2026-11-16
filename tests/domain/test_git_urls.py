from django.test import SimpleTestCase

from src.domain.git_urls import is_web_url, project_name_from_url


class ProjectNameFromUrlTests(SimpleTestCase):
    def test_uses_the_repository_name(self):
        for url, name in (
            ("https://github.com/acme/task-pulse", "task-pulse"),
            ("https://github.com/acme/task-pulse.git", "task-pulse"),
            ("https://github.com/acme/task-pulse/", "task-pulse"),
            ("git@github.com:acme/task-pulse.git", "task-pulse"),
            ("git@github.com:task-pulse.git", "task-pulse"),
            ("https://git.acme.com/", "git.acme.com"),  # no path: the host
        ):
            with self.subTest(url=url):
                self.assertEqual(project_name_from_url(url), name)


class IsWebUrlTests(SimpleTestCase):
    def test_only_http_and_https_can_be_links(self):
        for url, expected in (
            ("https://github.com/acme/portal", True),
            ("HTTP://git.acme.local/portal", True),
            ("git@github.com:acme/portal.git", False),
            ("javascript:alert(1)", False),
        ):
            with self.subTest(url=url):
                self.assertIs(is_web_url(url), expected)
