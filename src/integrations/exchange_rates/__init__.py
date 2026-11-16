"""Current US dollar -> Brazilian real exchange rate.

Callers depend on the ``ExchangeRateProvider`` protocol (one method,
``usd_brl()``), not on a concrete API. ``default_provider()`` builds the one
the app uses: AwesomeAPI behind a cache. Optional settings:
``EXCHANGE_RATE_API_URL``, ``EXCHANGE_RATE_TIMEOUT`` (seconds) and
``EXCHANGE_RATE_CACHE_SECONDS``.
"""

from django.conf import settings
from django.core.cache import cache

from .awesomeapi import DEFAULT_TIMEOUT, DEFAULT_URL, AwesomeApiProvider
from .base import ExchangeRate, ExchangeRateProvider, ExchangeRateUnavailable
from .caching import CachedProvider

DEFAULT_CACHE_SECONDS = 10 * 60
CACHE_KEY = "tasks:exchange_rate:USD-BRL"

__all__ = [
    "ExchangeRate",
    "ExchangeRateProvider",
    "ExchangeRateUnavailable",
    "default_provider",
]


def default_provider():
    return CachedProvider(
        AwesomeApiProvider(
            url=getattr(settings, "EXCHANGE_RATE_API_URL", DEFAULT_URL),
            timeout=getattr(settings, "EXCHANGE_RATE_TIMEOUT", DEFAULT_TIMEOUT),
        ),
        cache=cache,
        key=CACHE_KEY,
        seconds=getattr(settings, "EXCHANGE_RATE_CACHE_SECONDS", DEFAULT_CACHE_SECONDS),
    )
