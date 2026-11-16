"""Dollar rate from AwesomeAPI (https://docs.awesomeapi.com.br/api-de-moedas).

Free, no key. The response looks like::

    {"USDBRL": {"code": "USD", "codein": "BRL", "bid": "5.3521",
                "create_date": "2026-11-16 10:00:00", ...}}

``bid`` (the price buyers pay for a dollar) is used: it is what converting
dollars you received into reais gives you.
"""

import json
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.request import Request, urlopen

from .base import ExchangeRate, ExchangeRateUnavailable

DEFAULT_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
DEFAULT_TIMEOUT = 5  # seconds
MAX_RESPONSE_BYTES = 64 * 1024


class AwesomeApiProvider:
    def __init__(self, url=DEFAULT_URL, timeout=DEFAULT_TIMEOUT, opener=urlopen):
        self.url = url
        self.timeout = timeout
        self._open = opener

    def usd_brl(self):
        return parse_response(self.fetch())

    def fetch(self):
        """Raw JSON text from the API."""
        request = Request(self.url, headers={"Accept": "application/json"})
        try:
            with self._open(request, timeout=self.timeout) as response:
                return response.read(MAX_RESPONSE_BYTES).decode("utf-8")
        except (URLError, TimeoutError, OSError, UnicodeDecodeError) as error:
            raise ExchangeRateUnavailable(
                f"Could not reach {self.url}: {error}"
            ) from error


def parse_response(text):
    """``ExchangeRate`` from the API's JSON text."""
    try:
        quote = json.loads(text)["USDBRL"]
        rate = Decimal(str(quote["bid"]))
        quoted_at = str(quote.get("create_date", ""))
    except (ValueError, KeyError, TypeError, InvalidOperation) as error:
        raise ExchangeRateUnavailable(f"Unexpected response: {text[:200]!r}") from error
    if not rate.is_finite() or rate <= 0:
        raise ExchangeRateUnavailable(f"Invalid rate: {rate}")
    return ExchangeRate(rate=rate, quoted_at=quoted_at)
