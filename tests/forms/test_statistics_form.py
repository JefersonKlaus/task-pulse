from datetime import date

from django.test import SimpleTestCase

from src.forms import StatisticsForm


def form(**data):
    return StatisticsForm(
        data={"inicio": "2026-01-01", "fim": "2026-11-30", "agrupar": "mes", **data}
    )


class StatisticsFormTests(SimpleTestCase):
    def test_first_visit_is_the_last_twelve_months_by_month(self):
        self.assertEqual(
            StatisticsForm.initial_data(date(2026, 11, 17)),
            {"inicio": "2025-12-01", "fim": "2026-11-30", "agrupar": "mes"},
        )

    def test_end_before_start_is_rejected(self):
        self.assertEqual(
            form(fim="2025-12-31").errors["fim"],
            ["A data final não pode ser anterior à inicial."],
        )

    def test_at_most_sixty_bars(self):
        for data, valid in (
            ({"inicio": "2021-12-01", "agrupar": "mes"}, True),  # 60 months
            ({"inicio": "2021-11-30", "agrupar": "mes"}, False),  # 61
            ({"inicio": "2025-10-13", "agrupar": "semana"}, True),  # 60 weeks
            # A Sunday: its week, from Monday 06/10, is the 61st.
            ({"inicio": "2025-10-12", "agrupar": "semana"}, False),
        ):
            with self.subTest(data=data):
                self.assertIs(form(**data).is_valid(), valid)

    def test_too_many_weeks_suggests_grouping_by_month(self):
        self.assertEqual(
            form(inicio="2020-01-01", agrupar="semana").non_field_errors(),
            ["Período longo demais: escolha até 60 semanas ou agrupe por mês."],
        )
        self.assertEqual(
            form(inicio="2020-01-01").non_field_errors(),
            ["Período longo demais: escolha até 60 meses."],
        )

    def test_an_unknown_grouping_is_only_a_field_error(self):
        invalid = form(agrupar="ano")
        self.assertEqual(list(invalid.errors), ["agrupar"])

    def test_an_invalid_date_is_only_a_field_error(self):
        invalid = form(inicio="31/02/2026")
        self.assertEqual(list(invalid.errors), ["inicio"])
