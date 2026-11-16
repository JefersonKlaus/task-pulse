"""Forms: validate what the user typed. One module per feature."""

from .dashboard import DashboardForm
from .fields import HoursMinutesField
from .projects import ProjectForm
from .task_import import TaskImportForm
from .tasks import TaskAddTimeForm, TaskCreateForm, TaskUpdateForm

__all__ = [
    "DashboardForm",
    "HoursMinutesField",
    "ProjectForm",
    "TaskAddTimeForm",
    "TaskCreateForm",
    "TaskImportForm",
    "TaskUpdateForm",
]
