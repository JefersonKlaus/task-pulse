from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ProjectForm, TaskAddTimeForm, TaskCreateForm
from ..models import Project


def project_list(request):
    projects = Project.objects.all()
    return render(request, "tasks/project_list.html", {"projects": projects})


def project_create(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        project = form.save()
        return redirect("tasks:project_detail", pk=project.pk)
    return render(request, "tasks/project_form.html", {"form": form})


def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("tasks:project_detail", pk=project.pk)
    return render(
        request,
        "tasks/project_form.html",
        {"form": form, "project": project},
    )


def project_detail(request, pk):
    """The project, its tasks, and the "Nova tarefa" form (POST creates)."""
    project = get_object_or_404(Project, pk=pk)
    task_form = TaskCreateForm(request.POST or None)
    if request.method == "POST" and task_form.is_valid():
        task = task_form.save(commit=False)
        task.project = project
        task.save()
        return redirect("tasks:project_detail", pk=project.pk)
    return render(
        request,
        "tasks/project_detail.html",
        {
            "project": project,
            "task_form": task_form,
            # One input per task row: no ids, so they don't clash.
            "add_time_form": TaskAddTimeForm(auto_id=False),
        },
    )
