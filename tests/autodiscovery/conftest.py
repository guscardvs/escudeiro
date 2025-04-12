import pathlib

import pytest


@pytest.fixture
def sample_root_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent.parent


@pytest.fixture
def mock_module_path(sample_root_path: pathlib.Path) -> pathlib.Path:
    return sample_root_path / "autodiscovery/modules"


@pytest.fixture
def sample_files(mock_module_path: pathlib.Path) -> list[pathlib.Path]:
    return list((mock_module_path).glob("**/*.py"))
