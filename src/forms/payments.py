from django import forms
from django.utils.translation import gettext_lazy as _

from .billing import BillingForm
from .fields import IdListField, money_input


class PaymentForm(BillingForm):
    """The "Pagar" dialog of the billing page (only with a company chosen).

    It carries the billing filter in hidden fields (the payment is
    recalculated from it), the ids of the tasks shown, and the amounts
    actually received. Registering is ``src.services.payments``.
    """

    pago_usd = forms.DecimalField(
        label=_("Pago (US$)"),
        min_value=0,
        max_digits=12,
        decimal_places=2,
        widget=money_input(_("Ex.: 635.00")),
    )
    pago_brl = forms.DecimalField(
        label=_("Pago (R$)"),
        min_value=0,
        max_digits=12,
        decimal_places=2,
        widget=money_input(_("Ex.: 3397.25")),
    )
    tarefas = IdListField(error_messages={"required": _("Não há tarefas a pagar.")})

    FILTER_FIELDS = tuple(BillingForm.base_fields)

    def __init__(self, *args, **kwargs):
        # Ids differ from the filter form's, which is on the same page.
        kwargs.setdefault("auto_id", "id_pagamento_%s")
        super().__init__(*args, **kwargs)
        for name in self.FILTER_FIELDS:
            self.fields[name].widget = self.fields[name].hidden_widget()
        # A payment is made by one company (see services.payments).
        self.fields["empresa"].required = True
        self.fields["empresa"].error_messages["required"] = _(
            "Escolha a empresa que está pagando."
        )

    @classmethod
    def for_report(cls, filter_form, report):
        """Unbound dialog for the filter on screen and its tasks to pay."""
        initial = {name: filter_form.cleaned_data[name] for name in cls.FILTER_FIELDS}
        initial["tarefas"] = [line.task.pk for line in report.to_pay.lines]
        return cls(initial=initial)
