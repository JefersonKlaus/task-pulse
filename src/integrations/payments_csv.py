"""Write the payments report (the Pagamentos page) as a CSV file.

One payment per line, in the order given (the page's: newest first)::

    Registrado em;Empresa;Início;Fim;Tarefas;Horas;Estimado (US$);...
    17/11/2026 14:30;Alignerr;01/11/2026;30/11/2026;2;7,75;460,00;...

Written the way Excel in Brazilian Portuguese opens it, like the file that
"Importar tarefas" reads:

* ";" separator and decimal comma, with no thousands separator or currency
  symbol, so the values are numbers a spreadsheet can add up;
* dates as dd/mm/aaaa, and the registration time in the app's time zone;
* UTF-8 with a BOM, so Excel shows the accents ("Diferença") correctly.

A value that doesn't exist (the estimate in reais when the exchange rate was
unavailable, and so its difference) is left empty. "Empresa" is the company
of the payment's tasks, "Várias empresas" when they are of several, or empty
when they have none. Like the rest of the file (for Excel in Portuguese), it
doesn't change with the language of the interface.
"""

import csv
import io

from django.utils import timezone

from ..domain.durations import decimal_hours

MIXED_PROVIDERS = "Várias empresas"

HEADER = (
    "Registrado em",
    "Empresa",
    "Início",
    "Fim",
    "Tarefas",
    "Horas",
    "Estimado (US$)",
    "Estimado (R$)",
    "Pago (US$)",
    "Pago (R$)",
    "Diferença (US$)",
    "Diferença (R$)",
)


def write_payments_csv(payments):
    """The CSV text, BOM included, of ``payments``.

    Each payment needs the ``task_count`` and ``minutes`` added by
    ``Payment.objects.with_task_totals()``.
    """
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(HEADER)
    for payment in payments:
        writer.writerow(
            (
                f"{timezone.localtime(payment.created_at):%d/%m/%Y %H:%M}",
                _provider(payment),
                f"{payment.period_start:%d/%m/%Y}",
                f"{payment.period_end:%d/%m/%Y}",
                payment.task_count,
                _number(decimal_hours(payment.minutes)),
                _number(payment.estimated_usd),
                _number(payment.estimated_brl),
                _number(payment.paid_usd),
                _number(payment.paid_brl),
                _number(payment.difference_usd),
                _number(payment.difference_brl),
            )
        )
    return output.getvalue()


def _provider(payment):
    if payment.mixes_providers:
        return MIXED_PROVIDERS
    return payment.provider_name or ""


def _number(value):
    """Decimal("-1234.50") -> "-1234,50"; None -> ""."""
    if value is None:
        return ""
    return f"{value:.2f}".replace(".", ",")
