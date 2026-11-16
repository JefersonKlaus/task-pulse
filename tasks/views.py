from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm, TaskForm
from .models import Project


def project_list(request):
    projects = Project.objects.select_related("repository").all()
    return render(request, "tasks/project_list.html", {"projects": projects})


def project_create(request):
    form = ProjectForm(request.POST or None)
    if form.is_valid():
        project = form.save()
        return redirect("tasks:project_detail", pk=project.pk)
    return render(request, "tasks/project_form.html", {"form": form})


def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("repository"),
        pk=pk,
    )
    task_form = TaskForm(request.POST or None)
    if request.method == "POST" and task_form.is_valid():
        task = task_form.save(commit=False)
        task.project = project
        task.save()
        return redirect("tasks:project_detail", pk=project.pk)
    return render(
        request,
        "tasks/project_detail.html",
        {"project": project, "task_form": task_form},
    )
