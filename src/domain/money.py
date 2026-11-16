"""Money: rounding, dollar-to-real conversion and display.

Dollars are shown US-style and reais Brazilian-style, whatever the page
locale: "US$ 1,234.50" and "R$ 1.234,50".
"""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def round_money(amount):
    """Round to cents, half up."""
    return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)


def usd_to_brl(amount_usd, rate):
    """Convert with ``rate`` reais per dollar, rounded to cents."""
    return round_money(amount_usd * rate)


def format_usd(amount):
    """Decimal("1234.5") -> "US$ 1,234.50"."""
    return f"US$ {_grouped(amount, ',', '.')}"


def format_brl(amount):
    """Decimal("1234.5") -> "R$ 1.234,50"."""
    return f"R$ {_grouped(amount, '.', ',')}"


def format_rate(rate):
    """Decimal("5.3521") -> "R$ 5,3521" (reais per dollar, 4 decimals)."""
    text = f"{Decimal(rate).quantize(Decimal('0.0001'), ROUND_HALF_UP):.4f}"
    return f"R$ {text.replace('.', ',')}"


def _grouped(amount, thousands, decimal):
    text = f"{round_money(amount):,.2f}"
    return text.replace(",", "\0").replace(".", decimal).replace("\0", thousands)
