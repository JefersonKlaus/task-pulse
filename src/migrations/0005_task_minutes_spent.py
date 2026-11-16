"""Store time spent as whole minutes instead of decimal hours.

Hours become minutes (2.50 -> 150), rounded half up. Minutes make repeated
"add time" operations exact; the hours total is computed for display.
Reversible: minutes are turned back into hours with two decimals.
"""

from decimal import ROUND_HALF_UP, Decimal

import django.core.validators
from django.db import migrations, models


def hours_to_minutes(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    for task in Task.objects.all():
        minutes = (task.time_spent * 60).to_integral_value(rounding=ROUND_HALF_UP)
        task.minutes_spent = int(minutes)
        task.save(update_fields=["minutes_spent"])


def minutes_to_hours(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    for task in Task.objects.all():
        hours = Decimal(task.minutes_spent) / 60
        task.time_spent = hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        task.save(update_fields=["time_spent"])


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0004_task_dates_and_text_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="minutes_spent",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Tempo gasto, em minutos.",
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.RunPython(hours_to_minutes, minutes_to_hours),
        migrations.RemoveField(
            model_name="task",
            name="time_spent",
        ),
    ]
