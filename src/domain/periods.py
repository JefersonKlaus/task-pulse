"""Date ranges, and splitting a period into months or weeks (for charts)."""

import calendar
from dataclasses import dataclass
from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

# For chart labels ("nov/26"); translated when the label is built. Literal
# calls, so that makemessages finds them.
MONTH_ABBREVIATIONS = (
    pgettext_lazy("abbreviated month", "jan"),
    pgettext_lazy("abbreviated month", "fev"),
    pgettext_lazy("abbreviated month", "mar"),
    pgettext_lazy("abbreviated month", "abr"),
    pgettext_lazy("abbreviated month", "mai"),
    pgettext_lazy("abbreviated month", "jun"),
    pgettext_lazy("abbreviated month", "jul"),
    pgettext_lazy("abbreviated month", "ago"),
    pgettext_lazy("abbreviated month", "set"),
    pgettext_lazy("abbreviated month", "out"),
    pgettext_lazy("abbreviated month", "nov"),
    pgettext_lazy("abbreviated month", "dez"),
)


def month_of(day):
    """``(first_day, last_day)`` of the month containing ``day``."""
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)


def months_before(day, months):
    """The first day of the month ``months`` months before ``day``'s month."""
    index = day.year * 12 + day.month - 1 - months
    return day.replace(year=index // 12, month=index % 12 + 1, day=1)


class Grouping(models.TextChoices):
    MONTH = "mes", _("Mês")
    WEEK = "semana", _("Semana")


@dataclass(frozen=True)
class Bucket:
    """One month or one week (Monday to Sunday) of a period."""

    start: object  # date
    end: object  # date
    label: str  # "nov/26" or "16/11" (the Monday)

    def __contains__(self, day):
        return self.start <= day <= self.end


def bucket_count(start, end, grouping):
    """How many months or weeks ``buckets()`` gives, without building them."""
    if grouping == Grouping.MONTH:
        return (end.year - start.year) * 12 + end.month - start.month + 1
    return (end - _monday_of(start)).days // 7 + 1


def buckets(start, end, grouping):
    """Every whole month or week that has a day in ``[start, end]``, in order.

    Whole: the first and last buckets can start before ``start`` or end
    after ``end``; only what happened in the period is counted in them.
    """
    if grouping == Grouping.MONTH:
        result, day = [], start.replace(day=1)
        while day <= end:
            first, last = month_of(day)
            result.append(
                Bucket(first, last, f"{MONTH_ABBREVIATIONS[day.month - 1]}/{day:%y}")
            )
            day = last + timedelta(days=1)
        return result
    mondays = (
        _monday_of(start) + timedelta(weeks=n)
        for n in range(bucket_count(start, end, grouping))
    )
    return [Bucket(day, day + timedelta(days=6), f"{day:%d/%m}") for day in mondays]


def _monday_of(day):
    return day - timedelta(days=day.weekday())
