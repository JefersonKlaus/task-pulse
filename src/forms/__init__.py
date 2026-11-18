"""Forms: validate what the user typed. One module per feature."""

from .billing import BillingForm
from .fields import HoursMinutesField
from .payments import PaymentForm
from .projects import ProjectForm
from .providers import ProviderFilterForm, ProviderForm
from .statistics import StatisticsForm
from .task_import import TaskImportForm
from .tasks import TaskAddTimeForm, TaskCreateForm, TaskUpdateForm

__all__ = [
    "BillingForm",
    "HoursMinutesField",
    "PaymentForm",
    "ProjectForm",
    "ProviderFilterForm",
    "ProviderForm",
    "StatisticsForm",
    "TaskAddTimeForm",
    "TaskCreateForm",
    "TaskImportForm",
    "TaskUpdateForm",
]
