"""Views: turn HTTP requests into service calls and results into pages.

One module per feature; ``urls.py`` imports them from here.
"""

from .billing import billing, billing_pay
from .payments import payment_export, payment_list
from .projects import project_create, project_detail, project_list, project_update
from .providers import provider_create, provider_list, provider_update
from .statistics import statistics
from .task_import import task_import
from .tasks import task_add_time, task_update

__all__ = [
    "billing",
    "billing_pay",
    "payment_export",
    "payment_list",
    "project_create",
    "project_detail",
    "project_list",
    "project_update",
    "provider_create",
    "provider_list",
    "provider_update",
    "statistics",
    "task_add_time",
    "task_import",
    "task_update",
]
