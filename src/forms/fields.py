"""Reusable form fields and widgets."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..domain.durations import HMM_PATTERN, format_hmm, parse_hmm
from ..models import Provider


def date_input():
    # <input type="date"> only understands ISO dates, whatever the locale.
    return forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})


def provider_filter():
    """The "Empresa" filter of the reports: a company, or all of them."""
    return forms.ModelChoiceField(
        label=_("Empresa"),
        queryset=Provider.objects.all(),
        required=False,
        empty_label=_("Todas as empresas"),
    )


def money_input(placeholder):
    return forms.NumberInput(
        attrs={"step": "0.01", "min": "0", "placeholder": placeholder}
    )


class HoursMinutesField(forms.Field):
    """Time typed as H:MM ("1:30"); cleaned to whole minutes (90)."""

    default_error_messages = {
        "invalid": _("Use o formato H:MM, por exemplo 1:30."),
        "zero": _("Informe um tempo maior que 0:00."),
    }

    def __init__(self, *, allow_zero=True, **kwargs):
        self.allow_zero = allow_zero
        kwargs.setdefault(
            "widget",
            forms.TextInput(
                attrs={
                    "placeholder": "H:MM",
                    "pattern": HMM_PATTERN,
                    "inputmode": "numeric",
                    "title": _("Formato H:MM, por exemplo 1:30"),
                }
            ),
        )
        super().__init__(**kwargs)

    def prepare_value(self, value):
        return format_hmm(value) if isinstance(value, int) else value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, int):
            return value
        try:
            return parse_hmm(str(value))
        except ValueError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")

    def validate(self, value):
        super().validate(value)
        if value == 0 and not self.allow_zero:
            raise ValidationError(self.error_messages["zero"], code="zero")


class IdListField(forms.Field):
    """Ids sent as repeated hidden inputs (tarefas=3&tarefas=7) -> [3, 7]."""

    widget = forms.MultipleHiddenInput
    hidden_widget = forms.MultipleHiddenInput
    default_error_messages = {"invalid": _("Lista de ids inválida.")}

    def to_python(self, value):
        if not value:
            return []
        try:
            return [int(item) for item in value]
        except (TypeError, ValueError):
            raise ValidationError(self.error_messages["invalid"], code="invalid")
