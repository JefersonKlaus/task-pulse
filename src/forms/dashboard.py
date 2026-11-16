from django import forms

from ..domain.periods import month_of
from ..domain.pricing import Pricing
from ..domain.task_status import TaskStatus
from .fields import date_input, money_input


class DashboardForm(forms.Form):
    """Period, statuses and rates for the dashboard (sent as GET parameters)."""

    inicio = forms.DateField(label="De", widget=date_input())
    fim = forms.DateField(label="Até", widget=date_input())
    status = forms.MultipleChoiceField(
        label="Status",
        choices=TaskStatus.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Tarefas listadas e calculadas. Nenhum marcado = todos.",
    )
    valor_hora = forms.DecimalField(
        label="Valor/h (US$)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=money_input("Ex.: 90.00"),
    )
    valor_flat = forms.DecimalField(
        label="Valor flat/h (US$)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=money_input("Ex.: 100.00"),
        help_text=(
            "Valor da última hora de cada tarefa não rejeitada. "
            "Vazio = todas as horas pelo valor/h."
        ),
    )
    bonus = forms.DecimalField(
        label="Bônus (US$)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=money_input("Ex.: 50.00"),
        help_text="Somado uma vez ao total do período.",
    )

    @staticmethod
    def initial_data(today):
        """Data for a first visit: the current month, every status."""
        start, end = month_of(today)
        return {
            "inicio": start.isoformat(),
            "fim": end.isoformat(),
            "status": list(TaskStatus.values),
        }

    def clean_status(self):
        return self.cleaned_data["status"] or list(TaskStatus.values)

    def clean(self):
        cleaned_data = super().clean()
        start, end = cleaned_data.get("inicio"), cleaned_data.get("fim")
        if start and end and end < start:
            self.add_error("fim", "A data final não pode ser anterior à inicial.")
        # Only when valor/h was left blank (not when it is already invalid).
        hourly_rate_blank = (
            "valor_hora" not in self.errors and cleaned_data.get("valor_hora") is None
        )
        if hourly_rate_blank:
            if cleaned_data.get("valor_flat") is not None:
                self.add_error(
                    "valor_hora", "Informe o valor/h para usar o valor flat."
                )
            if cleaned_data.get("bonus") is not None:
                self.add_error("valor_hora", "Informe o valor/h para usar o bônus.")
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
