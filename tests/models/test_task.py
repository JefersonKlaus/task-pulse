from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from src.models import Task
from tests.factories import build_task, create_project, create_task


class TaskDefaultsTests(TestCase):
    def test_new_task_is_doing_started_today_without_finish_or_time(self):
        task = Task.objects.create(project=create_project(), name="Nova")
        self.assertEqual(
            (task.status, task.started_on, task.finished_on, task.minutes_spent),
            ("DOING", timezone.localdate(), None, 0),
        )


class TaskValidationTests(TestCase):
    def setUp(self):
        self.project = create_project()

    def test_finish_before_start_is_rejected(self):
        task = build_task(
            self.project, started_on=date(2026, 3, 10), finished_on=date(2026, 3, 9)
        )
        with self.assertRaises(ValidationError) as raised:
            task.full_clean()
        self.assertIn("finished_on", raised.exception.message_dict)

    def test_finish_on_the_start_day_is_accepted(self):
        build_task(
            self.project, started_on=date(2026, 3, 10), finished_on=date(2026, 3, 10)
        ).full_clean()

    def test_negative_minutes_are_rejected(self):
        with self.assertRaises(ValidationError):
            build_task(self.project, minutes_spent=-1).full_clean()

    def test_every_status_fits_the_column(self):
        max_length = Task._meta.get_field("status").max_length
        self.assertLessEqual(
            max(len(value) for value in Task.Status.values), max_length
        )


class TaskFinishDateOnSaveTests(TestCase):
    """save() applies the Término rule using the task's *stored* state."""

    TODAY = date(2026, 11, 20)

    def setUp(self):
        patcher = mock.patch("src.models.timezone.localdate", return_value=self.TODAY)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.task = create_task(started_on=date(2026, 11, 16), minutes_spent=180)

    def save(self, **values):
        for field, value in values.items():
            setattr(self.task, field, value)
        self.task.save()
        self.task.refresh_from_db()

    def test_moving_to_done_sets_today(self):
        self.save(status="DONE")
        self.assertEqual(self.task.finished_on, self.TODAY)

    def test_approving_a_rejected_task_uses_today_not_its_old_date(self):
        self.save(status="REJECTED", finished_on=date(2026, 11, 18))
        self.save(status="DONE")
        self.assertEqual(self.task.finished_on, self.TODAY)

    def test_back_to_doing_clears_the_date_but_keeps_the_time(self):
        self.save(status="REVIEW")
        self.save(status="DOING")
        self.assertEqual((self.task.finished_on, self.task.minutes_spent), (None, 180))


class TaskAddTimeTests(TestCase):
    def setUp(self):
        self.task = create_task(minutes_spent=0)

    def test_additions_accumulate_exactly(self):
        for minutes in (120, 60, 20, 20, 20):
            self.task.add_time(minutes)
        self.task.refresh_from_db()
        self.assertEqual(self.task.minutes_spent, 240)

    def test_a_stale_copy_does_not_lose_an_addition(self):
        stale_copy = Task.objects.get(pk=self.task.pk)
        self.task.add_time(60)
        stale_copy.add_time(30)
        self.task.refresh_from_db()
        self.assertEqual(self.task.minutes_spent, 90)


class TaskExternalIdTests(TestCase):
    """The id from another system is unique per project (blank is free)."""

    def setUp(self):
        self.project = create_project()

    def test_blank_id_is_allowed_for_many_tasks(self):
        create_task(self.project)
        create_task(self.project)
        self.assertEqual(self.project.tasks.filter(external_id="").count(), 2)

    def test_same_id_is_allowed_in_another_project(self):
        create_task(self.project, external_id="TP-1")
        create_task(create_project(name="Outro"), external_id="TP-1")
        self.assertEqual(Task.objects.filter(external_id="TP-1").count(), 2)

    def test_duplicate_id_in_a_project_fails_validation(self):
        create_task(self.project, external_id="TP-1")
        with self.assertRaises(ValidationError) as raised:
            build_task(self.project, external_id="TP-1").full_clean()
        self.assertIn(
            "Já existe uma tarefa com este ID externo neste projeto.",
            raised.exception.messages,
        )

    def test_duplicate_id_in_a_project_is_blocked_by_the_database(self):
        create_task(self.project, external_id="TP-1")
        with self.assertRaises(IntegrityError):
            create_task(self.project, external_id="TP-1")
