from django.shortcuts import render
from django.utils import timezone

from ..forms import DashboardForm
from ..integrations.exchange_rates import default_provider
from ..services.dashboard import build_dashboard


def dashboard(request):
    form = DashboardForm(
        request.GET or DashboardForm.initial_data(timezone.localdate())
    )
    report = None
    if form.is_valid():
        report = build_dashboard(
            start=form.cleaned_data["inicio"],
            end=form.cleaned_data["fim"],
            statuses=form.cleaned_data["status"],
            pricing=form.pricing(),
            exchange_rates=default_provider(),
        )
    return render(request, "tasks/dashboard.html", {"form": form, "report": report})
