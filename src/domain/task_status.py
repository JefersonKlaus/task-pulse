"""The statuses a task goes through."""

from django.db import models


class TaskStatus(models.TextChoices):
    DOING = "DOING", "Doing"
    REVIEW = "REVIEW", "Review"
    DONE = "DONE", "Done"
    REJECTED = "REJECTED", "Rejeitado"


# Moving into one of these statuses marks the task as finished.
FINISHED_STATUSES = (TaskStatus.REVIEW, TaskStatus.DONE)
