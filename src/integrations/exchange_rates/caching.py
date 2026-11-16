"""Keep a provider's answer for a while, so the API is not called on every
page view. Failures are never cached."""


class CachedProvider:
    def __init__(self, provider, cache, key, seconds):
        self.provider = provider
        self.cache = cache
        self.key = key
        self.seconds = seconds

    def usd_brl(self):
        rate = self.cache.get(self.key)
        if rate is None:
            rate = self.provider.usd_brl()
            self.cache.set(self.key, rate, self.seconds)
        return rate
