from django.contrib import admin

from .models import Project, Repository, Task


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name", "description")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "repository", "created_at")
    list_filter = ("repository",)
    search_fields = ("name", "repository__name")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "nickname",
        "project",
        "external_id",
        "time_spent",
        "date",
        "status",
    )
    list_filter = ("status", "project__repository", "date")
    search_fields = ("nickname", "external_id")
