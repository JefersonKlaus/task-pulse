"""How much work is worth, in US dollars.

Per task:

* Every hour is paid at the hourly rate ("valor/h").
* Tasks that were not rejected have their **last hour** paid at the flat
  rate ("valor flat/h") instead: 5h at $90 with a $100 flat is
  4 x 90 + 1 x 100 = $460.
* A task with less than one hour has all of it paid at the flat rate
  (0:30 with a $100 flat = $50).
* Without a flat rate, every hour is paid at the hourly rate (5 x 90 = $450).
* Rejected tasks never get the flat rate.

Per period, an optional bonus is added once to the total of the tasks.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import round_money
from .task_status import TaskStatus

FLAT_MINUTES = 60  # the "last hour"


def earns_flat_rate(status):
    """Only tasks that were not rejected get the flat last hour."""
    return status != TaskStatus.REJECTED


@dataclass(frozen=True)
class Pricing:
    hourly_rate: Decimal
    flat_rate: Decimal | None = None
    bonus: Decimal | None = None

    def task_value(self, minutes, status):
        """Value of ``minutes`` of work on one task, rounded to cents."""
        flat_minutes = 0
        if self.flat_rate is not None and earns_flat_rate(status):
            flat_minutes = min(minutes, FLAT_MINUTES)
        amount = (minutes - flat_minutes) * self.hourly_rate
        if flat_minutes:
            amount += flat_minutes * self.flat_rate
        return round_money(Decimal(amount) / 60)
