from django import forms
from django.utils.translation import gettext_lazy as _

from ..domain.periods import Grouping, bucket_count, month_of, months_before
from .fields import date_input, provider_filter

# More bars than this don't fit a chart.
MAX_BARS = 60


class StatisticsForm(forms.Form):
    """Company, period and grouping of the Estatísticas page (GET parameters)."""

    empresa = provider_filter()
    inicio = forms.DateField(label=_("De"), widget=date_input())
    fim = forms.DateField(label=_("Até"), widget=date_input())
    agrupar = forms.ChoiceField(label=_("Agrupar por"), choices=Grouping.choices)

    @staticmethod
    def initial_data(today):
        """A first visit: the last 12 months, this one included, by month."""
        return {
            "inicio": months_before(today, 11).isoformat(),
            "fim": month_of(today)[1].isoformat(),
            "agrupar": Grouping.MONTH,
        }

    def clean(self):
        cleaned_data = super().clean()
        start, end = cleaned_data.get("inicio"), cleaned_data.get("fim")
        grouping = cleaned_data.get("agrupar")
        if start and end:
            if end < start:
                self.add_error(
                    "fim", _("A data final não pode ser anterior à inicial.")
                )
            elif grouping and bucket_count(start, end, grouping) > MAX_BARS:
                message = (
                    _("Período longo demais: escolha até %(max)s meses.")
                    if grouping == Grouping.MONTH
                    else _(
                        "Período longo demais: escolha até %(max)s semanas "
                        "ou agrupe por mês."
                    )
                )
                self.add_error(None, message % {"max": MAX_BARS})
        return cleaned_data
