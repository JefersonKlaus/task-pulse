"""Time spent on tasks: stored as whole minutes, typed as H:MM, shown in hours.

Minutes are exact, so adding 0:20 three times gives exactly 1:00 (1.00h).
Rounding to two decimals only happens when the total is displayed.
"""

import re
from decimal import ROUND_HALF_UP, Decimal

# Hours (1-4 digits) ":" minutes (00-59). Also used as the HTML `pattern`.
HMM_PATTERN = "[0-9]{1,4}:[0-5][0-9]"
_HMM_RE = re.compile(rf"^{HMM_PATTERN}$")


def parse_hmm(value):
    """ "3:30" -> 210 (minutes). Raises ValueError for anything else."""
    value = value.strip()
    if not _HMM_RE.match(value):
        raise ValueError(f"Not in H:MM format: {value!r}")
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


# Decimal hours with a comma or a dot: "3,8", "3.8", "2".
_DECIMAL_HOURS_RE = re.compile(r"^[0-9]{1,4}(?:[.,][0-9]+)?$")


def parse_decimal_hours(value):
    """ "3,8" or "3.8" -> 228 (minutes), rounded half up. Raises ValueError."""
    value = value.strip()
    if not _DECIMAL_HOURS_RE.match(value):
        raise ValueError(f"Not decimal hours: {value!r}")
    hours = Decimal(value.replace(",", "."))
    return int((hours * 60).to_integral_value(rounding=ROUND_HALF_UP))


def format_hmm(minutes):
    """210 -> "3:30"."""
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}"


def decimal_hours(minutes):
    """210 -> Decimal("3.50"); rounded half up to two decimals."""
    return (Decimal(minutes) / 60).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_decimal_hours(minutes):
    """210 -> "3.50h"."""
    return f"{decimal_hours(minutes)}h"
