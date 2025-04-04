from typing import Any

from escudeiro.config import DotFile, Env, EnvConfig, EnvMapping


def test_env_cast_default():
    environ = EnvMapping({"MY_ENV_VAR": Env.LOCAL.name})
    dotfile = DotFile(filename="mydotfile", env=Env.TEST)
    config = EnvConfig(dotfile, env_var="MY_ENV_VAR", mapping=environ)

    # Define your test cases for the default env_cast
    test_cases = [
        ("local", Env.LOCAL),
        ("test", Env.TEST),
        ("dev", Env.DEV),
        ("qa", Env.QA),
        ("prd", Env.PRD),
    ]

    for input_value, expected_env in test_cases:
        result_env = config.env_cast(input_value)
        assert result_env == expected_env


def test_env_cast_custom_handler():
    def custom_env_cast(input_value: Any):
        # Custom logic for casting environment names to Env enum values
        if input_value == "custom":
            return Env.DEV
        return Env.PRD  # Default if custom value not recognized

    environ = EnvMapping({"MY_ENV_VAR": Env.LOCAL.name})
    dotfile = DotFile(filename="mydotfile", env=Env.TEST)
    config = EnvConfig(
        dotfile, env_var="MY_ENV_VAR", mapping=environ, env_cast=custom_env_cast
    )

    # Define your test cases for the custom env_cast
    test_cases = [
        ("local", Env.PRD),
        ("test", Env.PRD),
        ("custom", Env.DEV),
        (
            "unknown",
            Env.PRD,
        ),  # Custom handler returns default for unknown values
    ]

    for input_value, expected_env in test_cases:
        result_env = config.env_cast(input_value)
        assert result_env == expected_env
