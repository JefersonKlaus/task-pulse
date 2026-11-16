from django.test import SimpleTestCase

from src.domain.durations import (
    format_decimal_hours,
    format_hmm,
    parse_decimal_hours,
    parse_hmm,
)


class ParseHmmTests(SimpleTestCase):
    """Time typed as H:MM becomes whole minutes."""

    def test_valid_values(self):
        for text, minutes in (
            ("3:30", 210),
            ("0:45", 45),
            ("12:05", 725),
            (" 1:30 ", 90),
            ("0:00", 0),
        ):
            with self.subTest(text=text):
                self.assertEqual(parse_hmm(text), minutes)

    def test_invalid_values(self):
        for text in ("3.5", "3", "1:5", "1:60", "-1:00", "12345:00", "٣:30", ""):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_hmm(text)


class ParseDecimalHoursTests(SimpleTestCase):
    """Decimal hours from CSV files ("3,8") become whole minutes."""

    def test_valid_values(self):
        for text, minutes in (
            ("3,8", 228),
            ("3.8", 228),
            ("2", 120),
            ("0,25", 15),
            ("1,999", 120),  # rounded to the nearest minute
        ):
            with self.subTest(text=text):
                self.assertEqual(parse_decimal_hours(text), minutes)

    def test_invalid_values(self):
        for text in ("", "-1", "3,", ",5", "1.234,5", "abc", "3:30"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_decimal_hours(text)


class FormatTests(SimpleTestCase):
    def test_hmm_pads_minutes(self):
        self.assertEqual((format_hmm(65), format_hmm(0)), ("1:05", "0:00"))

    def test_decimal_hours_have_two_decimals(self):
        # 3:30 -> 3.50h; 0:20 -> 0.33h
        self.assertEqual(
            (format_decimal_hours(210), format_decimal_hours(20)), ("3.50h", "0.33h")
        )
