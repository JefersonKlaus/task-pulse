from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ProviderForm
from ..models import Provider


def provider_list(request):
    """The companies, with how many projects each has."""
    # Explicit order: Django ignores Meta.ordering in queries with aggregates.
    providers = Provider.objects.annotate(project_count=Count("projects")).order_by(
        "name"
    )
    return render(request, "tasks/provider_list.html", {"providers": providers})


def provider_create(request):
    form = ProviderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("tasks:provider_list")
    return render(request, "tasks/provider_form.html", {"form": form})


def provider_update(request, pk):
    provider = get_object_or_404(Provider, pk=pk)
    form = ProviderForm(request.POST or None, instance=provider)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("tasks:provider_list")
    return render(
        request, "tasks/provider_form.html", {"form": form, "provider": provider}
    )
