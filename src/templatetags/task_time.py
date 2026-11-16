from django import template

from ..domain.durations import format_decimal_hours, format_hmm

register = template.Library()


@register.filter
def decimal_hours(minutes):
    """{{ task.minutes_spent|decimal_hours }} -> "3.50h"."""
    return format_decimal_hours(minutes)


@register.filter
def hmm(minutes):
    """{{ task.minutes_spent|hmm }} -> "3:30"."""
    return format_hmm(minutes)
