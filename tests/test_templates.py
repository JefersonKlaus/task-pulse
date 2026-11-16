import re
from pathlib import Path

from django.test import SimpleTestCase

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "templates"


class TemplateTests(SimpleTestCase):
    def test_every_post_form_has_a_csrf_token(self):
        # Django's test client skips CSRF checks, so the page tests would not
        # notice a missing token; real browsers would get "403 Forbidden".
        for path in TEMPLATES.rglob("*.html"):
            for form in re.findall(
                r'<form[^>]*method="post".*?</form>',
                path.read_text(encoding="utf-8"),
                re.S,
            ):
                with self.subTest(template=path.name):
                    self.assertIn("{% csrf_token %}", form)
