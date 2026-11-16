from django.contrib import messages
from django.shortcuts import redirect, render

from ..forms import TaskImportForm
from ..services.task_import import import_tasks


def task_import(request):
    form = TaskImportForm(
        request.POST or None,
        request.FILES or None,
        # /importar/?projeto=<pk> preselects a project (link on its page).
        initial={"project": request.GET.get("projeto")},
    )
    if request.method == "POST" and form.is_valid():
        project, result = import_tasks(form.rows, form.destination())
        messages.success(
            request,
            f"{result.total} linha(s) processada(s) em “{project.name}”: "
            f"{result.created} tarefa(s) criada(s), {result.skipped} "
            "ignorada(s) (id já existente no projeto).",
        )
        return redirect("tasks:project_detail", pk=project.pk)
    return render(request, "tasks/task_import.html", {"form": form})
