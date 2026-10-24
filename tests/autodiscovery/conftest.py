import importlib
import pathlib
import sys
from collections.abc import Callable, Iterator

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


@pytest.fixture
def make_package(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[[str, dict[str, str]], pathlib.Path]]:
    """Create `tmp_path/<name>` from {relative path: source} and make it importable."""

    def make(name: str, files: dict[str, str]) -> pathlib.Path:
        root = tmp_path / name
        root.mkdir()
        (root / "__init__.py").touch()
        for relpath, source in files.items():
            file = root / relpath
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(source)
        monkeypatch.syspath_prepend(str(tmp_path))
        return root

    yield make

    # drop tmp packages so they don't leak into other tests
    for name, mod in list(sys.modules.items()):
        if str(getattr(mod, "__file__", None) or "").startswith(str(tmp_path)):
            del sys.modules[name]
    importlib.invalidate_caches()
