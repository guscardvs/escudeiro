import pathlib
import sys

# Import the code to be tested
from escudeiro.autodiscovery.base import (
    AutoDiscoveryHelper,
    make_modulename_converter,
    smart_import,
    sort_files_by_dependency,
)


def test_make_modulename_converter(sample_root_path: pathlib.Path):
    path_converter = pathlib.Path.as_posix
    converter = make_modulename_converter(sample_root_path, path_converter)
    sample_path = sample_root_path / "subdir/module.py"
    assert converter(sample_path) == "tests.subdir.module"


def test_auto_discovery_helper_excludes(sample_root_path: pathlib.Path):
    helper = AutoDiscoveryHelper(
        root=sample_root_path,
        exclude=["exclude_dir"],
    )
    excludes = helper.excludes
    assert "exclude_dir" in excludes[0]


def test_auto_discovery_helper_includes(sample_root_path: pathlib.Path):
    helper = AutoDiscoveryHelper(root=sample_root_path, include=["include_dir"])
    includes = helper.includes
    assert "include_dir" in includes[0]


def test_auto_discovery_helper_should_look(
    sample_root_path: pathlib.Path, tmp_path: pathlib.Path
):
    helper = AutoDiscoveryHelper(
        root=sample_root_path,
        exclude=["exclude_dir"],
        include=["file.py"],
    )
    path_to_check = tmp_path / "file.py"
    assert helper.should_lookup(path_to_check)

    exclude_path = tmp_path / "exclude_dir"
    assert not helper.should_lookup(exclude_path)

    not_included = tmp_path / "not_included.py"
    assert not helper.should_lookup(not_included)


def test_sort_files_by_dependency(
    sample_root_path: pathlib.Path, sample_files: list[pathlib.Path]
):
    converter = make_modulename_converter(
        sample_root_path, pathlib.Path.as_posix
    )
    files = sorted(sample_files)
    modnames = list(map(converter, files))
    names = [path.stem for path in sort_files_by_dependency(modnames, files)]
    assert names.index("mod_a") < names.index("mod_b") < names.index("mod_c")


def test_smart_import():
    def resolver(path: pathlib.Path):
        return path.stem

    imported_mod = smart_import("tests.autodiscovery.modules", resolver)
    second = smart_import("tests.autodiscovery.modules", resolver)
    assert imported_mod == second
    # Check that the module was imported only once
    assert imported_mod.value == 1

    # Clean up sys.modules
    del sys.modules["tests.autodiscovery.modules"]
