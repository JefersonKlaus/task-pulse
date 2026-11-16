"""Reusable form fields and widgets."""

from django import forms
from django.core.exceptions import ValidationError

from ..domain.durations import HMM_PATTERN, format_hmm, parse_hmm


def date_input():
    # <input type="date"> only understands ISO dates, whatever the locale.
    return forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})


def money_input(placeholder):
    return forms.NumberInput(
        attrs={"step": "0.01", "min": "0", "placeholder": placeholder}
    )


class HoursMinutesField(forms.Field):
    """Time typed as H:MM ("1:30"); cleaned to whole minutes (90)."""

    default_error_messages = {
        "invalid": "Use o formato H:MM, por exemplo 1:30.",
        "zero": "Informe um tempo maior que 0:00.",
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
                    "title": "Formato H:MM, por exemplo 1:30",
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
