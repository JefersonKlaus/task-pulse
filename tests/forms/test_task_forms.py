from datetime import date

from django.test import SimpleTestCase, TestCase

from src.forms import TaskCreateForm, TaskUpdateForm
from tests.factories import build_task, create_task
from tests.payloads import task_update_data


class TaskCreateFormTests(SimpleTestCase):
    def test_asks_only_name_goals_and_how_to_validate(self):
        self.assertEqual(
            list(TaskCreateForm().fields),
            ["name", "description", "acceptance_criteria"],
        )


class TaskUpdateFormLockTests(SimpleTestCase):
    """Término is locked while the (submitted) status is DOING; time never is."""

    def test_finish_date_is_locked_for_a_doing_task(self):
        fields = TaskUpdateForm(instance=build_task(status="DOING")).fields
        self.assertEqual(
            (fields["finished_on"].disabled, fields["minutes_spent"].disabled),
            (True, False),
        )

    def test_the_submitted_status_decides(self):
        for submitted, stored, locked in (
            ("REVIEW", "DOING", False),
            ("DOING", "DONE", True),
        ):
            form = TaskUpdateForm(
                data=task_update_data(status=submitted),
                instance=build_task(status=stored),
            )
            with self.subTest(submitted=submitted):
                self.assertIs(form.fields["finished_on"].disabled, locked)

    def test_doing_ignores_a_submitted_finish_date(self):
        form = TaskUpdateForm(
            data=task_update_data(status="DOING", finished_on="2026-11-18"),
            instance=build_task(status="DOING"),
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["finished_on"])


class TaskUpdateFormTests(SimpleTestCase):
    def test_added_time_is_summed_to_the_total(self):
        form = TaskUpdateForm(
            data=task_update_data(minutes_spent="2:00", add_time="1:15")
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["minutes_spent"], 195)

    def test_finish_before_start_is_rejected(self):
        form = TaskUpdateForm(
            data=task_update_data(started_on="2026-11-16", finished_on="2026-11-15")
        )
        self.assertEqual(
            form.errors["finished_on"],
            ["A data de término não pode ser anterior ao início."],
        )

    def test_dates_are_rendered_in_iso_for_the_browser(self):
        # <input type="date"> only understands ISO dates, whatever the locale.
        # (Checks the visible input: Django also renders a hidden
        # "initial-started_on" input, which is always ISO.)
        form = TaskUpdateForm(
            instance=build_task(status="DONE", started_on=date(2026, 11, 16))
        )
        self.assertIn(
            'type="date" name="started_on" value="2026-11-16"', str(form["started_on"])
        )


class TaskUpdateFormExternalIdTests(TestCase):
    def setUp(self):
        self.task = create_task(external_id="TP-1")

    def test_rejects_the_id_of_another_task_in_the_project(self):
        other = create_task(self.task.project, external_id="TP-2")
        form = TaskUpdateForm(data=task_update_data(external_id="TP-1"), instance=other)
        self.assertEqual(
            form.errors["external_id"],
            ["Já existe uma tarefa com este ID externo neste projeto."],
        )

    def test_accepts_its_own_id(self):
        form = TaskUpdateForm(
            data=task_update_data(external_id="TP-1"), instance=self.task
        )
        self.assertTrue(form.is_valid(), form.errors)
