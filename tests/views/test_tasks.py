from datetime import date
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from tests.factories import create_project, create_task
from tests.payloads import task_update_data


class TaskUpdateViewTests(TestCase):
    TODAY = date(2026, 11, 20)

    def setUp(self):
        self.project = create_project(name="Portal do Cliente")
        self.task = create_task(
            self.project,
            name="Tela de login",
            started_on=date(2026, 11, 16),
            minutes_spent=90,
        )
        self.url = reverse("tasks:task_update", args=[self.task.pk])

    def test_shows_the_current_values(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'value="Tela de login"')
        self.assertContains(response, 'name="started_on" value="2026-11-16"')  # ISO
        self.assertContains(response, 'value="1:30"')  # time as H:MM

    def test_finish_date_is_locked_while_doing(self):
        content = self.client.get(self.url).content.decode()
        self.assertRegex(content, r'<input [^>]*name="finished_on"[^>]*disabled')
        self.assertIn('status.value === "DOING"', content)  # unlocked by script

    def test_done_sets_todays_finish_date_and_saves_the_time(self):
        with mock.patch("src.models.timezone.localdate", return_value=self.TODAY):
            response = self.client.post(
                self.url,
                task_update_data(
                    status="DONE", finished_on="", minutes_spent="1:30", add_time="2:00"
                ),
            )
        self.task.refresh_from_db()
        self.assertRedirects(
            response, reverse("tasks:project_detail", args=[self.project.pk])
        )
        self.assertEqual(
            (self.task.finished_on, self.task.minutes_spent), (self.TODAY, 210)
        )

    def test_invalid_data_shows_the_error_and_changes_nothing(self):
        response = self.client.post(
            self.url,
            task_update_data(
                status="DONE", started_on="2026-11-16", finished_on="2026-11-15"
            ),
        )
        self.assertContains(
            response, "A data de término não pode ser anterior ao início."
        )
        self.task.refresh_from_db()
        self.assertEqual((self.task.status, self.task.finished_on), ("DOING", None))

    def test_unknown_task_is_not_found(self):
        url = reverse("tasks:task_update", args=[99999])
        self.assertEqual(self.client.get(url).status_code, 404)


class TaskAddTimeViewTests(TestCase):
    def setUp(self):
        self.project = create_project(name="Portal do Cliente")
        self.task = create_task(self.project, name="Tela de login", minutes_spent=0)
        self.url = reverse("tasks:task_add_time", args=[self.task.pk])

    def add(self, time):
        return self.client.post(self.url, {"time": time}, follow=True)

    def minutes(self):
        self.task.refresh_from_db()
        return self.task.minutes_spent

    def test_adds_time_and_confirms_the_new_total(self):
        self.add("2:00")
        response = self.add("1:30")
        self.assertEqual(self.minutes(), 210)
        self.assertRedirects(
            response, reverse("tasks:project_detail", args=[self.project.pk])
        )
        self.assertContains(
            response, "1:30 adicionado a “Tela de login”. Total: 3.50h."
        )

    def test_invalid_time_is_explained_and_not_added(self):
        for time, message in (
            ("2.5", "Use o formato H:MM, por exemplo 1:30."),
            ("0:00", "Informe um tempo maior que 0:00."),
        ):
            with self.subTest(time=time):
                self.assertContains(
                    self.add(time), f"Tempo não adicionado a “Tela de login”: {message}"
                )
                self.assertEqual(self.minutes(), 0)

    def test_only_post_is_allowed(self):
        self.assertEqual(self.client.get(self.url, {"time": "2:00"}).status_code, 405)
        self.assertEqual(self.minutes(), 0)
