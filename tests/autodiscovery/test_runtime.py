import pathlib

from escudeiro import autodiscovery
from escudeiro.misc import filter_isinstance, filter_issubclass


def test_runtime_autodiscovery_childof(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    Test = __import__(
        "tests.autodiscovery.modules.mod_a", fromlist=["Test"]
    ).Test
    runtime = autodiscovery.RuntimeAutoDiscovery(
        autodiscovery.runtime_child_of(Test),
        sample_root_path,
        mock_module_path,
    )
    result = dict(runtime)

    assert result
    assert list(filter_issubclass(Test, result.values()))


def test_runtime_autodiscovery_instanceof(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    Test = __import__(
        "tests.autodiscovery.modules.mod_a", fromlist=["Test"]
    ).Test
    runtime = autodiscovery.RuntimeAutoDiscovery(
        autodiscovery.runtime_instance_of(Test),
        sample_root_path,
        mock_module_path,
    )
    result = dict(runtime)

    assert result
    assert list(filter_isinstance(Test, result.values()))


def test_runtime_autodiscovery_contains_attr(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    runtime = autodiscovery.RuntimeAutoDiscovery(
        autodiscovery.runtime_contains_attr("name"),
        sample_root_path,
        mock_module_path,
    )
    result = dict(runtime)

    assert result
    assert all(hasattr(item, "name") for item in result.values())


def test_runtime_autodiscovery_attr_with_value(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    runtime = autodiscovery.RuntimeAutoDiscovery(
        autodiscovery.runtime_attr_with_value("abstract", False),
        sample_root_path,
        mock_module_path,
    )
    result = dict(runtime)

    assert result
    assert all(
        hasattr(item, "abstract") and item.abstract is False
        for item in result.values()
    )


def test_runtime_autodiscovery_chain_validate_all(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    Test = __import__(
        "tests.autodiscovery.modules.mod_a", fromlist=["Test"]
    ).Test
    runtime = autodiscovery.RuntimeAutoDiscovery(
        autodiscovery.runtime_chain_validate_all(
            autodiscovery.runtime_child_of(Test),
            autodiscovery.runtime_attr_with_value("abstract", False),
        ),
        sample_root_path,
        mock_module_path,
    )
    result = dict(runtime)

    assert result
    assert list(filter_issubclass(Test, result.values()))
    assert all(
        hasattr(item, "abstract") and item.abstract is False
        for item in result.values()
    )


def test_runtime_autodiscovery_chain_validate_any(
    sample_root_path: pathlib.Path, mock_module_path: pathlib.Path
):
    Test = __import__(
        "tests.autodiscovery.modules.mod_a", fromlist=["Test"]
    ).Test
    runtime = autodiscovery.RuntimeAutoDiscovery(
        autodiscovery.runtime_chain_validate_any(
            autodiscovery.runtime_child_of(Test),
            autodiscovery.runtime_attr_with_value("abstract", False),
        ),
        sample_root_path,
        mock_module_path,
    )
    result = dict(runtime)

    assert result
    assert all(
        (isinstance(item, type) and issubclass(item, Test))
        or (hasattr(item, "abstract") and item.abstract is False)
        for item in result.values()
    )
    assert any(
        not isinstance(item, type) or not issubclass(item, Test)
        for item in result.values()
    )
    assert any(
        not hasattr(item, "abstract") or item.abstract is not False
        for item in result.values()
    )
