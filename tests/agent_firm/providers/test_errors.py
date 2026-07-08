from engine.agent_firm.providers.errors import (
    ProviderException, ProviderQuotaExceeded, ProviderRateLimited,
    ProviderTimeout, ProviderUnavailable,
)


def test_all_provider_exceptions_are_provider_exception():
    for cls in (ProviderQuotaExceeded, ProviderRateLimited, ProviderTimeout, ProviderUnavailable):
        assert issubclass(cls, ProviderException)
        assert issubclass(cls, Exception)


def test_provider_exception_carries_message():
    err = ProviderTimeout("claude CLI timed out after 75s")
    assert str(err) == "claude CLI timed out after 75s"
