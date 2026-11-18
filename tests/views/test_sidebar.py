from django.test import TestCase
from django.urls import reverse

LINKS = {
    "tasks:statistics": "Estatísticas",
    "tasks:billing": "Faturamento",
    "tasks:payment_list": "Pagamentos",
    "tasks:project_list": "Projetos",
    "tasks:provider_list": "Empresas",
    "tasks:task_import": "Importar tarefas",
}


class SidebarTests(TestCase):
    def test_every_page_links_to_every_section(self):
        for page in (*LINKS, "tasks:project_create"):
            response = self.client.get(reverse(page))
            for name in LINKS:
                with self.subTest(page=page, link=name):
                    self.assertContains(response, f'href="{reverse(name)}"')

    def test_the_current_section_is_highlighted(self):
        for name, label in LINKS.items():
            response = self.client.get(reverse(name))
            with self.subTest(page=name):
                self.assertContains(
                    response,
                    f'<a href="{reverse(name)}" class="active">{label}</a>',
                    html=True,
                )
                self.assertEqual(response.content.decode().count('class="active"'), 1)
