"""Views: turn HTTP requests into service calls and results into pages.

One module per feature; ``urls.py`` imports them from here.
"""

from .dashboard import dashboard
from .projects import project_create, project_detail, project_list, project_update
from .task_import import task_import
from .tasks import task_add_time, task_update

__all__ = [
    "dashboard",
    "project_create",
    "project_detail",
    "project_list",
    "project_update",
    "task_add_time",
    "task_import",
    "task_update",
]
