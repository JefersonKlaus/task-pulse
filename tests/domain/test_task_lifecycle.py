from datetime import date

from django.test import SimpleTestCase

from src.domain.task_lifecycle import resolve_finished_on

TODAY = date(2026, 11, 20)
TYPED = date(2026, 11, 18)
STORED = date(2026, 11, 10)


class ResolveFinishedOnTests(SimpleTestCase):
    """The finish date ("Término") a task gets when it is saved."""

    def test_decision_table(self):
        # status, finished_on being saved, stored status, stored date -> result
        for label, status, finished_on, before, stored, expected in (
            ("DOING never has one", "DOING", TYPED, "DONE", STORED, None),
            ("into REVIEW: today", "REVIEW", None, "DOING", None, TODAY),
            ("into DONE: today", "DONE", None, "DOING", None, TODAY),
            ("created as DONE: today", "DONE", None, None, None, TODAY),
            ("typed date wins", "DONE", TYPED, "DOING", None, TYPED),
            ("stored date is not typed", "REVIEW", STORED, "REJECTED", STORED, TODAY),
            ("REVIEW to DONE keeps it", "DONE", STORED, "REVIEW", STORED, STORED),
            ("later correction kept", "DONE", TYPED, "DONE", STORED, TYPED),
            ("REJECTED keeps typed", "REJECTED", TYPED, "DOING", None, TYPED),
            ("REJECTED does not fill", "REJECTED", None, "DOING", None, None),
        ):
            with self.subTest(label):
                self.assertEqual(
                    resolve_finished_on(
                        status=status,
                        finished_on=finished_on,
                        previous_status=before,
                        previous_finished_on=stored,
                        today=TODAY,
                    ),
                    expected,
                )
