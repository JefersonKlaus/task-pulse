from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("projetos/novo/", views.project_create, name="project_create"),
    path("projetos/<int:pk>/", views.project_detail, name="project_detail"),
    path("projetos/<int:pk>/editar/", views.project_update, name="project_update"),
    path("tarefas/<int:pk>/editar/", views.task_update, name="task_update"),
    path("tarefas/<int:pk>/tempo/", views.task_add_time, name="task_add_time"),
    path("importar/", views.task_import, name="task_import"),
    path("painel/", views.dashboard, name="dashboard"),
]
