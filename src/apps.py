from django.apps import AppConfig


class TasksConfig(AppConfig):
    """The application is the ``src`` package.

    Its label stays "tasks", so database tables (tasks_task), migrations,
    permissions and content types are the same as before the move.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "src"
    label = "tasks"
