import pathlib
from types import ModuleType

from escudeiro import autodiscovery
from escudeiro.misc import filter_isinstance, filter_issubclass


def test_static_autodiscovery_childof(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    Test = __import__(
        "tests.autodiscovery.modules.mod_a", fromlist=["Test"]
    ).Test
    static = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_child_of(Test),
        sample_root_path,
        mock_module_path,
    )
    result = dict(static)

    assert result
    assert list(filter_issubclass(Test, result.values()))


def test_static_autodiscovery_instanceof(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    Test = __import__(
        "tests.autodiscovery.modules.mod_a", fromlist=["Test"]
    ).Test
    static = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_instance_of(Test),
        sample_root_path,
        mock_module_path,
    )
    result = dict(static)

    assert result
    assert list(filter_isinstance(Test, result.values()))


def test_static_autodiscovery_autoload(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    static = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_autoload_validator(),
        sample_root_path,
        mock_module_path,
    )
    result = dict(static)

    assert result
    assert list(filter_isinstance(ModuleType, result.values()))
    assert hasattr(next(iter(result.values()), None), "Counter")


def test_static_autodiscovery_module(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    static = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_modulename_validator(r"mod_a$"),
        sample_root_path,
        mock_module_path,
    )
    result = dict(static)

    assert result
    assert list(filter_isinstance(ModuleType, result.values()))
    assert hasattr(next(iter(result.values()), None), "Test")


def test_static_autodiscovery_chain_validate_any(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    Test = __import__(
        "tests.autodiscovery.modules.mod_a", fromlist=["Test"]
    ).Test
    EvenOther = __import__(
        "tests.autodiscovery.modules.mod_b", fromlist=["EvenOther"]
    ).EvenOther
    static = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_chain_validate(
            "any",
            autodiscovery.static_instance_of(Test),
            autodiscovery.static_instance_of(EvenOther),
        ),
        sample_root_path,
        mock_module_path,
    )
    result = dict(static)

    assert result
    assert all(
        isinstance(item, Test) or isinstance(item, EvenOther)
        for item in result.values()
    )
