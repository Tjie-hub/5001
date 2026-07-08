"""Provider name -> class lookup (design doc §4a). The Router resolves
providers by name through this module — it never imports a concrete
provider class directly."""

from typing import Callable

_PROVIDERS: dict[str, Callable[..., "FirmLLMProvider"]] = {}  # noqa: F821 (forward ref, avoids import cycle)


def register(name: str):
    def deco(cls):
        _PROVIDERS[name] = cls
        return cls
    return deco


def build(name: str, **kwargs):
    if name not in _PROVIDERS:
        raise ValueError(f"unknown provider {name!r}; registered: {sorted(_PROVIDERS)}")
    return _PROVIDERS[name](**kwargs)


def registered_names() -> list[str]:
    return sorted(_PROVIDERS)
