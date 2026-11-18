"""The statuses a task goes through."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class TaskStatus(models.TextChoices):
    DOING = "DOING", _("Doing")
    REVIEW = "REVIEW", _("Review")
    DONE = "DONE", _("Done")
    REJECTED = "REJECTED", _("Rejeitado")


# Moving into one of these statuses marks the task as finished.
FINISHED_STATUSES = (TaskStatus.REVIEW, TaskStatus.DONE)
