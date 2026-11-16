from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..domain.durations import format_decimal_hours, format_hmm
from ..forms import TaskAddTimeForm, TaskUpdateForm
from ..models import Task


def task_update(request, pk):
    task = get_object_or_404(Task.objects.select_related("project"), pk=pk)
    form = TaskUpdateForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("tasks:project_detail", pk=task.project_id)
    return render(request, "tasks/task_form.html", {"form": form, "task": task})


@require_POST
def task_add_time(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskAddTimeForm(request.POST)
    if form.is_valid():
        added = form.cleaned_data["time"]
        task.add_time(added)
        messages.success(
            request,
            f"{format_hmm(added)} adicionado a “{task.name}”. "
            f"Total: {format_decimal_hours(task.minutes_spent)}.",
        )
    else:
        messages.error(
            request,
            f"Tempo não adicionado a “{task.name}”: {form.errors['time'][0]}",
        )
    return redirect("tasks:project_detail", pk=task.project_id)
