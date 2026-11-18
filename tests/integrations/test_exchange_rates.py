import json
import socket
from decimal import Decimal
from unittest import mock
from urllib.error import HTTPError, URLError

from django.core.cache import cache
from django.core.cache.backends.locmem import LocMemCache
from django.test import SimpleTestCase, override_settings

from src.integrations.exchange_rates import (
    ExchangeRate,
    ExchangeRateUnavailable,
    default_provider,
)
from src.integrations.exchange_rates.awesomeapi import (
    DEFAULT_URL,
    MAX_RESPONSE_BYTES,
    AwesomeApiProvider,
    parse_response,
)
from src.integrations.exchange_rates.caching import CachedProvider

RATE = ExchangeRate(Decimal("5.3521"), "2026-11-16 10:00:00")
BODY = json.dumps(
    {"USDBRL": {"bid": "5.3521", "ask": "5.36", "create_date": "2026-11-16 10:00:00"}}
)


def fake_opener(body=BODY.encode()):
    """Stands in for urllib's urlopen (injected, nothing is patched)."""
    response = mock.MagicMock()
    response.read.return_value = body
    response.__enter__.return_value = response
    return mock.Mock(return_value=response)


class AwesomeApiTests(SimpleTestCase):
    def test_reads_the_bid_rate_and_its_time(self):
        self.assertEqual(parse_response(BODY), RATE)

    def test_rejects_unexpected_responses(self):
        for text in (
            "<html>erro</html>",
            "[]",
            json.dumps({"status": 404}),
            json.dumps({"USDBRL": {"ask": "5.3"}}),
            *(
                json.dumps({"USDBRL": {"bid": bid}})
                for bid in ("abc", "0", "-5", "Infinity")
            ),
        ):
            with self.subTest(text=text), self.assertRaises(ExchangeRateUnavailable):
                parse_response(text)

    def test_calls_the_url_with_a_timeout(self):
        opener = fake_opener()
        rate = AwesomeApiProvider(
            url="https://x.test/r", timeout=3, opener=opener
        ).usd_brl()
        request = opener.call_args.args[0]
        self.assertEqual(rate, RATE)
        self.assertEqual(request.full_url, "https://x.test/r")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(opener.call_args.kwargs["timeout"], 3)

    def test_response_size_is_limited(self):
        # A broken or hostile server can't make the page read without limit.
        opener = fake_opener()
        AwesomeApiProvider(opener=opener).usd_brl()
        response = opener.return_value
        response.read.assert_called_once_with(MAX_RESPONSE_BYTES)

    def test_network_problems_become_unavailable(self):
        for error in (
            URLError("Name or service not known"),
            HTTPError(DEFAULT_URL, 429, "Too Many Requests", {}, None),
            socket.timeout("timed out"),
        ):
            provider = AwesomeApiProvider(opener=mock.Mock(side_effect=error))
            with self.subTest(error=error), self.assertRaises(ExchangeRateUnavailable):
                provider.usd_brl()


class CachedProviderTests(SimpleTestCase):
    def setUp(self):
        self.inner = mock.Mock()
        # Same-named LocMemCaches share a store: start each test empty.
        self.cache = LocMemCache("test-exchange-rates", {})
        self.cache.clear()
        self.addCleanup(self.cache.clear)
        self.provider = CachedProvider(self.inner, self.cache, key="rate", seconds=600)

    def test_second_call_uses_the_cache(self):
        self.inner.usd_brl.return_value = RATE
        self.assertEqual(
            (self.provider.usd_brl(), self.provider.usd_brl()), (RATE, RATE)
        )
        self.assertEqual(self.inner.usd_brl.call_count, 1)

    def test_failures_are_not_cached(self):
        self.inner.usd_brl.side_effect = [ExchangeRateUnavailable("offline"), RATE]
        with self.assertRaises(ExchangeRateUnavailable):
            self.provider.usd_brl()
        self.assertEqual(self.provider.usd_brl(), RATE)


class DefaultProviderTests(SimpleTestCase):
    def test_awesomeapi_behind_djangos_cache_with_defaults(self):
        provider = default_provider()
        self.assertIs(provider.cache, cache)
        self.assertEqual(
            (provider.provider.url, provider.provider.timeout, provider.seconds),
            (DEFAULT_URL, 5, 600),
        )

    @override_settings(
        EXCHANGE_RATE_API_URL="https://x.test/r",
        EXCHANGE_RATE_TIMEOUT=1,
        EXCHANGE_RATE_CACHE_SECONDS=30,
    )
    def test_settings_override_the_defaults(self):
        provider = default_provider()
        self.assertEqual(
            (provider.provider.url, provider.provider.timeout, provider.seconds),
            ("https://x.test/r", 1, 30),
        )
