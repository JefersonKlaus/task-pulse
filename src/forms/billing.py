from django import forms
from django.utils.translation import gettext_lazy as _

from ..domain.periods import month_of
from ..domain.pricing import Pricing
from ..domain.task_status import TaskStatus
from .fields import date_input, money_input, provider_filter


class BillingForm(forms.Form):
    """Company, period, statuses and rates for the billing page (sent as GET
    parameters)."""

    empresa = provider_filter()
    inicio = forms.DateField(label=_("De"), widget=date_input())
    fim = forms.DateField(label=_("Até"), widget=date_input())
    status = forms.MultipleChoiceField(
        label=_("Status"),
        choices=TaskStatus.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Tarefas listadas e calculadas. Nenhum marcado = todos."),
    )
    pagas = forms.BooleanField(
        label=_("Incluir tarefas pagas"),
        required=False,
        help_text=_(
            "Desmarcado: as tarefas já pagas não são listadas nem calculadas."
        ),
    )
    valor_hora = forms.DecimalField(
        label=_("Valor/h (US$)"),
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=money_input(_("Ex.: 90.00")),
    )
    valor_flat = forms.DecimalField(
        label=_("Valor flat/h (US$)"),
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=money_input(_("Ex.: 100.00")),
        help_text=_(
            "Valor da última hora de cada tarefa não rejeitada. "
            "Vazio = todas as horas pelo valor/h."
        ),
    )
    bonus = forms.DecimalField(
        label=_("Bônus (US$)"),
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=money_input(_("Ex.: 50.00")),
        help_text=_("Somado uma vez ao total do período."),
    )

    @staticmethod
    def initial_data(today):
        """Data for a first visit: the current month, every status, paid
        tasks included. (Once the filter is submitted, an unchecked box is
        simply not sent, so it can't default to checked.)"""
        start, end = month_of(today)
        return {
            "inicio": start.isoformat(),
            "fim": end.isoformat(),
            "status": list(TaskStatus.values),
            "pagas": True,
        }

    def clean_status(self):
        return self.cleaned_data["status"] or list(TaskStatus.values)

    def clean(self):
        cleaned_data = super().clean()
        start, end = cleaned_data.get("inicio"), cleaned_data.get("fim")
        if start and end and end < start:
            self.add_error("fim", _("A data final não pode ser anterior à inicial."))
        # Only when valor/h was left blank (not when it is already invalid).
        hourly_rate_blank = (
            "valor_hora" not in self.errors and cleaned_data.get("valor_hora") is None
        )
        if hourly_rate_blank:
            if cleaned_data.get("valor_flat") is not None:
                self.add_error(
                    "valor_hora", _("Informe o valor/h para usar o valor flat.")
                )
            if cleaned_data.get("bonus") is not None:
                self.add_error("valor_hora", _("Informe o valor/h para usar o bônus."))
        return cleaned_data

    def pricing(self):
        """``Pricing`` from the rates, or ``None`` without a valor/h."""
        hourly_rate = self.cleaned_data["valor_hora"]
        if hourly_rate is None:
            return None
        return Pricing(
            hourly_rate=hourly_rate,
            flat_rate=self.cleaned_data["valor_flat"],
            bonus=self.cleaned_data["bonus"],
        )
