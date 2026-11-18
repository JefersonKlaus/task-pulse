from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_safe

from ..forms import ProviderFilterForm
from ..services.payments import payment_history, payments_csv


def payment_list(request):
    """Payments registered from the billing page, newest first, 10 per page;
    of one company with ?empresa=<id>."""
    filter_form = ProviderFilterForm(request.GET)
    provider = filter_form.provider()
    history = payment_history(request.GET.get("pagina"), provider=provider)
    page = history.page
    return render(
        request,
        "tasks/payment_list.html",
        {
            "history": history,
            "filter_form": filter_form,
            "provider": provider,
            # Page links keep the company filter: ?empresa=3&pagina=2
            "page_link": f"?empresa={provider.pk}&pagina=" if provider else "?pagina=",
            # 1 … 4 5 [6] 7 8 … 20
            "page_range": page.paginator.get_elided_page_range(
                page.number, on_each_side=2, on_ends=1
            ),
        },
    )


@require_safe
def payment_export(request):
    """Every payment (of ?empresa=<id>) as a CSV file to download."""
    provider = ProviderFilterForm(request.GET).provider()
    response = HttpResponse(
        payments_csv(provider), content_type="text/csv; charset=utf-8"
    )
    filename = f"pagamentos-{timezone.localdate():%Y-%m-%d}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
