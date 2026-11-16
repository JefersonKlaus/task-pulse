from django.test import SimpleTestCase
from django.template.loader import get_template


class TemplateLoadingTests(SimpleTestCase):
    def test_base_template_loads(self):
        template = get_template("tasks/base.html")
        self.assertIsNotNone(template)

    def test_project_list_template_loads(self):
        template = get_template("tasks/project_list.html")
        self.assertIsNotNone(template)

    def test_project_form_template_loads(self):
        template = get_template("tasks/project_form.html")
        self.assertIsNotNone(template)

    def test_project_detail_template_loads(self):
        template = get_template("tasks/project_detail.html")
        self.assertIsNotNone(template)

    def test_base_template_has_title_block(self):
        template = get_template("tasks/base.html")
        rendered = template.template.source
        self.assertIn("{% block title %}", rendered)

    def test_base_template_has_content_block(self):
        template = get_template("tasks/base.html")
        rendered = template.template.source
        self.assertIn("{% block content %}", rendered)

    def test_project_list_template_links_to_create_view(self):
        template = get_template("tasks/project_list.html")
        self.assertIn("tasks:project_create", template.template.source)

    def test_project_form_template_posts_form(self):
        template = get_template("tasks/project_form.html")
        self.assertIn('<form method="post">', template.template.source)

    def test_project_detail_template_posts_task_form(self):
        template = get_template("tasks/project_detail.html")
        self.assertIn('<form method="post">', template.template.source)

    def test_templates_include_csrf_tokens(self):
        for name in (
            "tasks/project_form.html",
            "tasks/project_detail.html",
        ):
            template = get_template(name)
            self.assertIn("{% csrf_token %}", template.template.source)
