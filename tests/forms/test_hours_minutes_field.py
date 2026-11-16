from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from src.forms import HoursMinutesField


class HoursMinutesFieldTests(SimpleTestCase):
    def test_cleans_hmm_to_minutes(self):
        self.assertEqual(HoursMinutesField().clean("3:30"), 210)

    def test_other_formats_get_a_hint(self):
        with self.assertRaises(ValidationError) as raised:
            HoursMinutesField().clean("3.5")
        self.assertEqual(
            raised.exception.messages, ["Use o formato H:MM, por exemplo 1:30."]
        )

    def test_zero_can_be_forbidden(self):
        with self.assertRaises(ValidationError) as raised:
            HoursMinutesField(allow_zero=False).clean("0:00")
        self.assertEqual(
            raised.exception.messages, ["Informe um tempo maior que 0:00."]
        )

    def test_blank_is_none_when_optional(self):
        self.assertIsNone(HoursMinutesField(required=False).clean(""))

    def test_accepts_stored_minutes(self):
        # Django cleans the stored value (an int) when a field is disabled.
        self.assertEqual(HoursMinutesField().clean(90), 90)

    def test_shows_minutes_as_hmm(self):
        self.assertEqual(HoursMinutesField().prepare_value(210), "3:30")
