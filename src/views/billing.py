from django.contrib import messages
from django.http import QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from ..domain.money import format_brl, format_usd
from ..forms import BillingForm, PaymentForm
from ..integrations.exchange_rates import default_provider
from ..services.billing import build_billing
from ..services.payments import PaymentError, register_payment


def billing(request):
    form = BillingForm(
        request.GET or BillingForm.initial_data(timezone.localdate())
    )
    return _render_billing(request, form)


@require_POST
def billing_pay(request):
    """The "Pagar" dialog: register the payment of the tasks shown.

    Invalid amounts show the billing page again with the dialog open; if the
    tasks changed meanwhile, the billing page is reloaded with a message.
    """
    payment_form = PaymentForm(request.POST)
    if payment_form.is_valid():
        data = payment_form.cleaned_data
        try:
            payment = register_payment(
                start=data["inicio"],
                end=data["fim"],
                statuses=data["status"],
                pricing=payment_form.pricing(),
                exchange_rates=default_provider(),
                task_ids=data["tarefas"],
                paid_usd=data["pago_usd"],
                paid_brl=data["pago_brl"],
                provider=data["empresa"],
            )
        except PaymentError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request,
                _("Pagamento registrado: %(count)s tarefa(s), %(usd)s e %(brl)s.")
                % {
                    "count": len(data["tarefas"]),
                    "usd": format_usd(payment.paid_usd),
                    "brl": format_brl(payment.paid_brl),
                },
            )
        return redirect(_billing_url(request.POST))
    return _render_billing(request, BillingForm(request.POST), payment_form)


def _render_billing(request, form, payment_form=None):
    report = None
    if form.is_valid():
        report = build_billing(
            start=form.cleaned_data["inicio"],
            end=form.cleaned_data["fim"],
            statuses=form.cleaned_data["status"],
            pricing=form.pricing(),
            exchange_rates=default_provider(),
            include_paid=form.cleaned_data["pagas"],
            provider=form.cleaned_data["empresa"],
        )
        # Paying needs the company that pays: without one, no dialog.
        if payment_form is None and report.to_pay and form.cleaned_data["empresa"]:
            payment_form = PaymentForm.for_report(form, report)
    return render(
        request,
        "tasks/billing.html",
        {"form": form, "report": report, "payment_form": payment_form},
    )


def _billing_url(data):
    """The billing page with the filter in ``data`` (the dialog's hidden fields)."""
    query = QueryDict(mutable=True)
    for name in PaymentForm.FILTER_FIELDS:
        query.setlist(name, data.getlist(name))  # absent fields stay out
    return f"{reverse('tasks:billing')}?{query.urlencode()}"
