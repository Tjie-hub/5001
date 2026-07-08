"""Provider-layer exception hierarchy. Every FirmLLMProvider.generate()
failure is re-raised as one of these four subclasses so the Router can act
on it uniformly regardless of which SDK/subprocess raised the original
error."""


class ProviderException(Exception):
    """Base class for all provider-layer failures the Router can act on."""


class ProviderQuotaExceeded(ProviderException):
    pass


class ProviderRateLimited(ProviderException):
    pass


class ProviderTimeout(ProviderException):
    pass


class ProviderUnavailable(ProviderException):
    pass
