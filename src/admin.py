from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .domain.durations import format_decimal_hours
from .models import Payment, Project, Provider, Task


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "url", "created_at")
    list_filter = ("provider",)
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

    @admin.display(description=_("Horas"), ordering="minutes_spent")
    def total_hours(self, task):
        return format_decimal_hours(task.minutes_spent)


class PaidTaskInline(admin.TabularInline):
    """The tasks of a payment, read-only: they are linked from the billing page."""

    model = Task
    fields = ("name", "external_id", "project", "status", "started_on", "hours")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description=_("Horas"))
    def hours(self, task):
        return format_decimal_hours(task.minutes_spent)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "estimated_usd",
        "estimated_brl",
        "paid_usd",
        "paid_brl",
        "created_at",
    )
    date_hierarchy = "period_start"
    inlines = [PaidTaskInline]
