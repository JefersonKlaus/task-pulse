from django import template

from ..domain.money import format_brl, format_rate, format_usd

register = template.Library()


@register.filter
def usd(amount):
    """{{ total|usd }} -> "US$ 1,234.50"."""
    return format_usd(amount)


@register.filter
def brl(amount):
    """{{ total|brl }} -> "R$ 1.234,50"."""
    return format_brl(amount)


@register.filter
def brl_rate(rate):
    """{{ rate|brl_rate }} -> "R$ 5,3521"."""
    return format_rate(rate)
