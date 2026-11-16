from django.contrib import admin

from .domain.durations import format_decimal_hours
from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "created_at")
    search_fields = ("name", "url", "description")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "external_id",
        "project",
        "status",
        "started_on",
        "finished_on",
        "total_hours",
    )
    list_filter = ("status", "project", "started_on")
    search_fields = ("name", "external_id", "description", "acceptance_criteria")

    @admin.display(description="Horas", ordering="minutes_spent")
    def total_hours(self, task):
        return format_decimal_hours(task.minutes_spent)
