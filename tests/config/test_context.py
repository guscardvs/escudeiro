import pytest

from escudeiro.config import get_config, get_env, set_config
from escudeiro.config.core.context import (
    _default_config,  # pyright: ignore[reportPrivateUsage]
    config,
)
from escudeiro.config.core.envconfig import EnvConfig
from escudeiro.config.core.mapping import EnvMapping
from escudeiro.exc.errors import AlreadySet


class TestConfigContext:
    @pytest.fixture(autouse=True)
    def clean_config(self, monkeypatch: pytest.MonkeyPatch):
        """
        A pytest fixture to ensure a clean state for each test.
        This replaces the setUp and tearDown methods from unittest.
        The `yield` keyword ensures that the `reset` happens after the test is run.
        """
        token = config.set(_default_config)
        monkeypatch.setenv("CONFIG_ENV", "test")
        yield
        config.reset(token)

    def test_get_config_returns_default_initially(self):
        """
        Test that get_config() returns the default configuration
        when no other configuration has been set.
        """
        assert get_config() is _default_config

    def test_set_config_successfully(self):
        """
        Test that set_config() successfully updates the configuration
        and that get_config() returns the new configuration.
        """
        new_config = EnvConfig()
        set_config(new_config)
        assert get_config() is new_config

    def test_set_config_raises_already_set_on_second_call(self):
        """
        Test that set_config() raises an AlreadySet error if it is
        called more than once in the same context.
        """
        # First, set the config successfully
        set_config(EnvConfig())

        # Now, try to set it again and assert that it raises the expected exception
        with pytest.raises(AlreadySet):
            set_config(EnvConfig())

    def test_get_env_returns_correct_value(self):
        """
        Test that get_env() returns the correct environment object
        after a new configuration has been set.
        """
        new_config = EnvConfig(mapping=EnvMapping({"CONFIG_ENV": "prd"}))
        set_config(new_config)

        assert get_env() is new_config.env
