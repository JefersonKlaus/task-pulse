from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.project_list, name="project_list"),
    path("projetos/novo/", views.project_create, name="project_create"),
    path("projetos/<int:pk>/", views.project_detail, name="project_detail"),
    path("projetos/<int:pk>/editar/", views.project_update, name="project_update"),
    path("empresas/", views.provider_list, name="provider_list"),
    path("empresas/nova/", views.provider_create, name="provider_create"),
    path("empresas/<int:pk>/editar/", views.provider_update, name="provider_update"),
    path("tarefas/<int:pk>/editar/", views.task_update, name="task_update"),
    path("tarefas/<int:pk>/tempo/", views.task_add_time, name="task_add_time"),
    path("importar/", views.task_import, name="task_import"),
    path("estatisticas/", views.statistics, name="statistics"),
    path("faturamento/", views.billing, name="billing"),
    path("faturamento/pagar/", views.billing_pay, name="billing_pay"),
    # The billing page was "Painel" (/painel/): old bookmarks, filter included.
    path(
        "painel/",
        RedirectView.as_view(pattern_name="tasks:billing", query_string=True),
    ),
    path("pagamentos/", views.payment_list, name="payment_list"),
    path("pagamentos/exportar/", views.payment_export, name="payment_export"),
]
