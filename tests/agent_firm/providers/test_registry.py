import pytest

from engine.agent_firm.providers import registry


def test_register_and_build():
    @registry.register("fake")
    class FakeProvider:
        name = "fake"
        def __init__(self, x=1):
            self.x = x

    p = registry.build("fake", x=5)
    assert isinstance(p, FakeProvider)
    assert p.x == 5


def test_build_unknown_raises_value_error():
    with pytest.raises(ValueError, match="unknown provider"):
        registry.build("nonexistent")


def test_registered_names_includes_registered():
    @registry.register("another_fake")
    class AnotherFake:
        name = "another_fake"

    assert "another_fake" in registry.registered_names()
