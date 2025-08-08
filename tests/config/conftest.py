import pytest


@pytest.fixture(autouse=True)
def no_env_vars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CONFIG_ENV", raising=False)
    monkeypatch.delenv("CONFIG_DOTFILE", raising=False)
    monkeypatch.delenv("NAME", raising=False)
    yield
