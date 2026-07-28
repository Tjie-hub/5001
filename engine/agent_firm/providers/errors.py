"""Provider-layer exception hierarchy. Every FirmLLMProvider.generate()
failure is re-raised as one of these subclasses so the Router can act on it
uniformly regardless of which SDK/subprocess raised the original error.

Each exception carries a ``category`` string (RCA 2026-07-10: failures must
be explicitly classified — session_limit_exceeded, rate_limited,
authentication_failed, timeout, network_failure, provider_unavailable,
unexpected_error, unknown). New leaf classes subclass the closest
pre-existing class so every ``except ProviderQuotaExceeded`` /
``except ProviderUnavailable`` call site keeps working unchanged.
"""


class ProviderException(Exception):
    """Base class for all provider-layer failures the Router can act on."""

    category: str = "unknown"

    def __init__(self, *args, category: str | None = None):
        super().__init__(*args)
        if category is not None:
            self.category = category


class ProviderQuotaExceeded(ProviderException):
    category = "quota_exceeded"


class ProviderSessionLimit(ProviderQuotaExceeded):
    """Subscription session/usage window exhausted. ``reset_time`` (aware
    datetime; None when the provider message carried no reset info) lets the
    Router hold the provider until the window reopens."""

    category = "session_limit_exceeded"

    def __init__(self, *args, reset_time=None, category: str | None = None):
        super().__init__(*args, category=category)
        self.reset_time = reset_time


class ProviderRateLimited(ProviderException):
    category = "rate_limited"


class ProviderTimeout(ProviderException):
    category = "timeout"


class ProviderUnavailable(ProviderException):
    category = "provider_unavailable"


class ProviderAuthFailed(ProviderUnavailable):
    category = "authentication_failed"


class ProviderNetworkFailure(ProviderUnavailable):
    category = "network_failure"


class ProviderUnexpectedError(ProviderUnavailable):
    category = "unexpected_error"
