from decimal import Decimal

from django.test import SimpleTestCase

from src.domain.charts import (
    Series,
    axis_step,
    bar_chart,
    compact_number,
    rows,
)

HOURS = [Series("paid", "Pagas"), Series("unpaid", "Não pagas")]


def chart(values, labels=None, **kwargs):
    labels = labels or [f"m{n}" for n in range(len(values))]
    kwargs.setdefault("format_value", lambda value: f"{value}h")
    kwargs.setdefault("format_tick", compact_number)
    return bar_chart(labels, HOURS, values, **kwargs)


class AxisStepTests(SimpleTestCase):
    def test_a_round_step_whose_four_steps_reach_the_highest_value(self):
        for highest, integer, step in (
            (Decimal("51.3"), False, Decimal("15")),  # axis 0-60
            (Decimal("60"), False, Decimal("15")),  # exactly the top
            (Decimal("90.05"), False, Decimal("25")),
            (Decimal("12000"), False, Decimal("3000")),
            (Decimal("0.2"), False, Decimal("0.05")),
            (0, False, Decimal("1")),  # no data: 0-4
            (Decimal("37"), True, Decimal("10")),
            (Decimal("10"), True, Decimal("3")),  # 2.5 is not a whole step
            (Decimal("3"), True, Decimal("1")),  # never below 1 task
        ):
            with self.subTest(highest=highest, integer=integer):
                self.assertEqual(axis_step(highest, integer=integer), step)
                self.assertGreaterEqual(step * 4, highest)


class BarChartTests(SimpleTestCase):
    def test_bars_are_stacked_in_percent_of_the_axis(self):
        # Highest bar 60 -> axis 0-60 in steps of 15.
        bars = chart([[Decimal(30), Decimal(15)], [Decimal(60), Decimal(0)]]).bars
        self.assertEqual(
            [[(s.key, s.percent) for s in bar.segments] for bar in bars],
            [[("paid", "50.00"), ("unpaid", "25.00")], [("paid", "100.00")]],
        )

    def test_ticks_from_zero_to_the_top(self):
        ticks = chart([[Decimal(51), Decimal(0)]]).ticks
        self.assertEqual(
            [(tick.label, tick.percent) for tick in ticks],
            [
                ("0", "0.00"),
                ("15", "25.00"),
                ("30", "50.00"),
                ("45", "75.00"),
                ("60", "100.00"),
            ],
        )

    def test_tooltip_has_every_value_and_the_total(self):
        (bar,) = chart([[Decimal(3), Decimal(2)]], labels=["nov/26"]).bars
        self.assertEqual(bar.title, "nov/26: Pagas 3h · Não pagas 2h · Total 5h")

    def test_one_series_has_no_total_in_the_tooltip(self):
        (bar,) = bar_chart(
            ["nov/26"],
            [Series("received", "Recebido")],
            [[Decimal(5)]],
            format_value=str,
            format_tick=str,
        ).bars
        self.assertEqual(bar.title, "nov/26: Recebido 5")

    def test_about_six_bars_are_labelled_when_space_is_short(self):
        for count, labelled in ((6, 6), (12, 6), (13, 5), (52, 6)):
            bars = chart([[Decimal(1), Decimal(0)]] * count).bars
            with self.subTest(count=count):
                self.assertFalse(bars[0].minor)
                self.assertEqual(sum(not bar.minor for bar in bars), labelled)

    def test_dense_with_more_than_sixteen_bars(self):
        self.assertFalse(chart([[1, 0]] * 16).dense)
        self.assertTrue(chart([[1, 0]] * 17).dense)

    def test_empty_when_every_value_is_zero(self):
        self.assertTrue(chart([[0, 0], [0, 0]]).empty)
        self.assertFalse(chart([[0, 0], [0, 1]]).empty)


class RowsTests(SimpleTestCase):
    def test_largest_first_in_percent_of_the_largest(self):
        result = rows(
            [("API", Decimal(30)), ("Portal", Decimal(120))], format_value=str
        )
        self.assertEqual(
            [(row.label, row.value, row.percent) for row in result],
            [("Portal", "120", "100.00"), ("API", "30", "25.00")],
        )

    def test_beyond_the_limit_the_smallest_are_added_up(self):
        items = [(f"p{n}", Decimal(n)) for n in range(1, 6)]  # p1..p5
        result = rows(items, format_value=str, limit=3)
        self.assertEqual(
            [(row.label, row.value) for row in result],
            [("p5", "5"), ("p4", "4"), ("Outros", "6")],  # 3 + 2 + 1
        )

    def test_nothing_to_show(self):
        self.assertEqual(rows([], format_value=str), [])
        (row,) = rows([("API", Decimal(0))], format_value=str)
        self.assertEqual(row.percent, "0.00")


class CompactNumberTests(SimpleTestCase):
    def test_short_axis_numbers(self):
        for value, text in (
            (Decimal("0"), "0"),
            (Decimal("1.50"), "1.5"),
            (Decimal("60"), "60"),
            (Decimal("2500"), "2.5k"),
            (Decimal("20000"), "20k"),
            (Decimal("1500000"), "1.5M"),
        ):
            with self.subTest(value=value):
                self.assertEqual(compact_number(value), text)
