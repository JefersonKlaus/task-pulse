from decimal import Decimal

from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..domain.charts import Series, bar_chart, compact_number, rows
from ..domain.durations import decimal_hours, format_decimal_hours
from ..domain.money import format_usd
from ..domain.periods import Grouping
from ..domain.task_status import TaskStatus
from ..forms import StatisticsForm
from ..services.statistics import build_statistics

HOURS = (Series("paid", _("Pagas")), Series("unpaid", _("Não pagas")))
# Stacked bottom to top: finished work first.
STATUSES = (TaskStatus.DONE, TaskStatus.REVIEW, TaskStatus.DOING, TaskStatus.REJECTED)
RECEIVED = (Series("received", _("Recebido")),)


def statistics(request):
    """Charts of the hours, tasks and money of a period."""
    form = StatisticsForm(
        request.GET or StatisticsForm.initial_data(timezone.localdate())
    )
    context = {"form": form}
    if form.is_valid():
        report = build_statistics(
            start=form.cleaned_data["inicio"],
            end=form.cleaned_data["fim"],
            grouping=form.cleaned_data["agrupar"],
            provider=form.cleaned_data["empresa"],
        )
        context.update(
            report=report,
            grouping_label=Grouping(form.cleaned_data["agrupar"]).label,
            by_week=form.cleaned_data["agrupar"] == Grouping.WEEK,
            **_charts(report),
        )
    return render(request, "tasks/statistics.html", context)


def _charts(report):
    labels = [stats.bucket.label for stats in report.buckets]
    return {
        "hours_chart": bar_chart(
            labels,
            HOURS,
            [
                [decimal_hours(stats.paid_minutes), decimal_hours(stats.unpaid_minutes)]
                for stats in report.buckets
            ],
            format_value=lambda hours: f"{hours:.2f}h",
            format_tick=lambda hours: f"{compact_number(hours)}h",
        ),
        "tasks_chart": bar_chart(
            labels,
            [Series(status.lower(), TaskStatus(status).label) for status in STATUSES],
            [
                [stats.tasks_by_status[status] for status in STATUSES]
                for stats in report.buckets
            ],
            format_value=str,
            format_tick=compact_number,
            integer=True,
        ),
        "received_chart": bar_chart(
            labels,
            RECEIVED,
            [[stats.received_usd] for stats in report.buckets],
            format_value=format_usd,
            format_tick=compact_number,
        ),
        "project_rows": rows(
            [
                (name, Decimal(minutes))
                for name, minutes in report.minutes_by_project.items()
            ],
            format_value=_hours,
        ),
        "provider_rows": rows(
            [
                (name or gettext("Sem empresa"), Decimal(minutes))
                for name, minutes in report.minutes_by_provider.items()
            ],
            format_value=_hours,
        ),
    }


def _hours(minutes):
    return format_decimal_hours(int(minutes))
