from wsgiref.util import setup_testing_defaults

from django.test import TestCase

from src.taskpulse.wsgi import application


class WsgiApplicationTests(TestCase):
    """The production entry point (``src.taskpulse.wsgi:application``) serves
    the app."""

    def test_serves_the_project_list(self):
        environ = {"PATH_INFO": "/", "HTTP_HOST": "testserver"}
        setup_testing_defaults(environ)
        started = {}

        def start_response(status, headers):
            started["status"] = status

        body = b"".join(application(environ, start_response))
        self.assertEqual(started["status"], "200 OK")
        self.assertIn("Nenhum projeto cadastrado.", body.decode())
