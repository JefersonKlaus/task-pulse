from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("projetos/novo/", views.project_create, name="project_create"),
    path("projetos/<int:pk>/", views.project_detail, name="project_detail"),
]
