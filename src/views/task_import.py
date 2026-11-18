from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

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
        imports = import_tasks(
            form.rows, form.destination(), provider=form.cleaned_data["provider"]
        )
        messages.success(request, _summary(imports))
        if len(imports) == 1:
            return redirect("tasks:project_detail", pk=imports[0].project.pk)
        return redirect("tasks:project_list")
    return render(request, "tasks/task_import.html", {"form": form})


def _summary(imports):
    """ "2 linha(s) processada(s) em “portal”: 2 tarefa(s) criada(s), …" """
    parts = [
        (
            _("“%(project)s” (projeto novo): %(created)s tarefa(s) criada(s), "
              "%(skipped)s ignorada(s)")
            if item.new
            else _("“%(project)s”: %(created)s tarefa(s) criada(s), "
                   "%(skipped)s ignorada(s)")
        )
        % {
            "project": item.project.name,
            "created": item.result.created,
            "skipped": item.result.skipped,
        }
        for item in imports
    ]
    values = {
        "lines": sum(item.result.total for item in imports),
        "projects": len(imports),
        "results": "; ".join(parts),
    }
    if len(imports) == 1:
        message = _(
            "%(lines)s linha(s) processada(s) em %(results)s "
            "(id já existente no projeto)."
        )
    else:
        message = _(
            "%(lines)s linha(s) processada(s) em %(projects)s projetos — "
            "%(results)s (id já existente no projeto)."
        )
    return message % values
