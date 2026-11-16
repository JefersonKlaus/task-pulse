"""Date ranges."""

import calendar


def month_of(day):
    """``(first_day, last_day)`` of the month containing ``day``."""
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)
