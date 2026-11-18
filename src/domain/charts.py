"""The geometry of the bar charts of the Estatísticas page.

Charts are drawn with HTML and CSS (no JavaScript): each bar and each axis
line is placed with a percentage of the chart's height, computed here.

* The axis goes from 0 to a round number ("top") in ``TICKS`` equal steps
  (0, 15, 30, 45, 60), a little above the highest bar.
* Percentages are strings with a dot ("64.25"), ready for CSS: numbers in
  templates are localized ("64,25" in Portuguese), which CSS doesn't read.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

TICKS = 4
# Round step sizes, times a power of ten: 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10.
STEPS = tuple(
    Decimal(step) for step in ("1", "1.5", "2", "2.5", "3", "4", "5", "6", "8", "10")
)
# In a narrow chart or with more than DENSE_BARS bars, only about this
# many bars are labelled (the labels would overlap).
LABELLED_BARS = 6
DENSE_BARS = 16


@dataclass(frozen=True)
class Series:
    key: str  # CSS class of its color
    label: str


@dataclass(frozen=True)
class Segment:
    key: str
    percent: str  # of the chart's height


@dataclass(frozen=True)
class Bar:
    label: str
    title: str  # tooltip: every value of the bar
    segments: list  # bottom to top
    # Minor bars are not labelled on phones, nor on the desktop when the
    # chart is dense (labels would overlap).
    minor: bool


@dataclass(frozen=True)
class Tick:
    label: str
    percent: str


@dataclass(frozen=True)
class BarChart:
    series: list
    bars: list
    ticks: list  # from 0 to the top
    dense: bool
    empty: bool  # every value is 0


@dataclass(frozen=True)
class Row:
    """A horizontal bar: a label and its value."""

    label: str
    value: str
    percent: str  # of the largest value


def axis_step(highest, *, integer=False):
    """The round step of an axis of ``TICKS`` steps that reaches ``highest``.

    ``integer``: counts (tasks) only get whole steps.
    """
    wanted = Decimal(highest) / TICKS
    if wanted <= 0:
        return Decimal(1)
    if integer:
        wanted = max(wanted, Decimal(1))
    magnitude = Decimal(10) ** wanted.adjusted()
    # 10 x magnitude is always >= wanted, and whole when wanted >= 1.
    return next(
        step
        for step in (step * magnitude for step in STEPS)
        if step >= wanted and (not integer or step == step.to_integral_value())
    )


def bar_chart(labels, series, values, *, format_value, format_tick, integer=False):
    """A chart with a (stacked) bar per label.

    ``values[i][j]`` is the value of ``series[j]`` in bar ``i``.
    ``format_value`` writes a value for the tooltip, ``format_tick`` for the
    axis.
    """
    totals = [sum(bar_values, Decimal(0)) for bar_values in values]
    step = axis_step(max(totals, default=0), integer=integer)
    top = step * TICKS
    every = math.ceil(len(labels) / LABELLED_BARS)
    bars = [
        Bar(
            label=label,
            title=_title(label, series, bar_values, total, format_value),
            segments=[
                Segment(one.key, _percent(value, top))
                for one, value in zip(series, bar_values)
                if value
            ],
            minor=index % every != 0,
        )
        for index, (label, bar_values, total) in enumerate(zip(labels, values, totals))
    ]
    return BarChart(
        series=list(series),
        bars=bars,
        ticks=[
            Tick(format_tick(step * n), _percent(step * n, top))
            for n in range(TICKS + 1)
        ],
        dense=len(labels) > DENSE_BARS,
        empty=not any(totals),
    )


def rows(items, *, format_value, limit=8, others=_("Outros")):
    """Horizontal bars for ``(label, value)`` pairs, largest first.

    Beyond ``limit`` rows, the smallest ones are added up into ``others``.
    """
    items = sorted(items, key=lambda item: item[1], reverse=True)
    if len(items) > limit:
        rest = sum((value for _, value in items[limit - 1 :]), Decimal(0))
        items = items[: limit - 1] + [(others, rest)]
    highest = max((value for _, value in items), default=0)
    return [
        Row(label, format_value(value), _percent(value, highest or 1))
        for label, value in items
    ]


def compact_number(value):
    """Axis numbers: Decimal("2500") -> "2.5k", Decimal("1.5") -> "1.5"."""
    value = Decimal(value)
    for size, suffix in ((Decimal(10) ** 6, "M"), (Decimal(1000), "k")):
        if abs(value) >= size:
            return f"{_plain(value / size)}{suffix}"
    return _plain(value)


def _plain(value):
    """Decimal("2.50") -> "2.5"; Decimal("20") -> "20" (never "2E+1")."""
    return f"{value.normalize():f}"


def _percent(value, top):
    return f"{Decimal(value) * 100 / top:.2f}"


def _title(label, series, values, total, format_value):
    parts = [f"{one.label} {format_value(value)}" for one, value in zip(series, values)]
    if len(series) > 1:
        parts.append(f"{gettext('Total')} {format_value(total)}")
    return f"{label}: {' · '.join(parts)}"
