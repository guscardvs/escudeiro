import os
import pathlib
import sys
from collections.abc import Callable
from types import ModuleType

import pytest

from escudeiro import autodiscovery
from escudeiro.autodiscovery.base import (
    AutoDiscoveryHelper,
    make_modulename_converter,
    smart_import,
    sort_files_by_dependency,
)

MakePackage = Callable[[str, dict[str, str]], pathlib.Path]

BASE = "class Base:\n    pass\n"


def resolver_for(root: pathlib.Path):
    return make_modulename_converter(root, pathlib.Path.as_posix)


def test_smart_import_uses_full_dotted_name(make_package: MakePackage):
    import json

    root = make_package("app", {"json.py": "MARK = 'app-json'\n"})
    mod = smart_import("app.json", resolver_for(root))

    assert mod.MARK == "app-json"
    assert sys.modules["json"] is json
    assert not hasattr(json, "MARK")


def test_smart_import_detects_main_by_file(
    make_package: MakePackage, monkeypatch: pytest.MonkeyPatch
):
    root = make_package(
        "app", {"runner.py": "raise RuntimeError('executed')\n"}
    )
    main = ModuleType("__main__")
    main.__file__ = str(root / "runner.py")
    monkeypatch.setitem(sys.modules, "__main__", main)

    assert smart_import("app.runner", resolver_for(root)) is main
    assert "app.runner" not in sys.modules


def test_modulename_of_init_is_the_package(make_package: MakePackage):
    root = make_package("app", {"sub/__init__.py": ""})
    convert = resolver_for(root)

    assert convert(root / "sub" / "__init__.py") == "app.sub"
    assert convert(root / "__init__.py") == "app"


def test_package_init_is_imported_once(
    make_package: MakePackage, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("AD_INIT_COUNT", "0")
    root = make_package(
        "app",
        {
            "sub/__init__.py": (
                "import os\n"
                "os.environ['AD_INIT_COUNT'] = "
                "str(int(os.environ['AD_INIT_COUNT']) + 1)\n"
                "class Marker:\n    pass\n"
            ),
            "sub/mod.py": "",
        },
    )
    discovery = autodiscovery.RuntimeAutoDiscovery(
        lambda obj: isinstance(obj, type) and obj.__name__ == "Marker", root
    )
    result = dict(discovery)

    assert os.environ["AD_INIT_COUNT"] == "1"
    assert "app.sub.__init__" not in sys.modules
    assert result == {"app.sub.Marker": sys.modules["app.sub"].Marker}


def test_include_filters_files_not_directories(make_package: MakePackage):
    root = make_package(
        "app",
        {
            "models.py": "",
            "other.py": "",
            "sub/models.py": "",
            "sub/deep/models.py": "",
            "sub/deep/other.py": "",
        },
    )
    helper = AutoDiscoveryHelper(root, include=["models.py"])
    found = sorted(p.relative_to(root).as_posix() for p in helper.iterdir(root))

    assert found == ["models.py", "sub/deep/models.py", "sub/models.py"]


def test_include_path_matches_directory_contents(make_package: MakePackage):
    root = make_package("app", {"a/x.py": "", "b/y.py": ""})
    helper = AutoDiscoveryHelper(root, include=[root / "a"])

    assert [p.name for p in helper.iterdir(root)] == ["x.py"]


def test_symlink_loop_is_not_followed(make_package: MakePackage):
    root = make_package("app", {"sub/mod.py": ""})
    try:
        os.symlink(root, root / "sub" / "loop", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    helper = AutoDiscoveryHelper(root)
    found = sorted(p.relative_to(root).as_posix() for p in helper.iterdir(root))

    assert found == ["__init__.py", "sub/mod.py"]


def test_sort_resolves_relative_imports(make_package: MakePackage):
    root = make_package(
        "app",
        {
            "a.py": "from . import b\n",
            "b.py": "from .c import X\n",
            "c.py": "X = 1\n",
        },
    )
    files = [root / "a.py", root / "b.py", root / "c.py"]
    names = ["app.a", "app.b", "app.c"]

    ordered = [p.name for p in sort_files_by_dependency(names, files)]
    assert ordered == ["c.py", "b.py", "a.py"]


def test_runtime_keys_are_module_qualified(make_package: MakePackage):
    root = make_package(
        "app",
        {
            "base.py": BASE,
            "models.py": "from app.base import Base\nclass A(Base): pass\n",
            "sub/models.py": "from app.base import Base\nclass A(Base): pass\n",
        },
    )
    base = __import__("app.base", fromlist=["Base"]).Base
    discovery = autodiscovery.RuntimeAutoDiscovery(
        autodiscovery.runtime_child_of(base), root
    )
    result = dict(discovery)

    assert sorted(result) == [
        "app.base.Base",
        "app.models.A",
        "app.sub.models.A",
    ]
    assert result["app.models.A"] is not result["app.sub.models.A"]
    assert discovery.asdict == result
    # imported base class is yielded once, not once per importing module
    assert len(list(discovery)) == 3


def test_runtime_reiteration(make_package: MakePackage):
    root = make_package("app", {"m.py": "class C: pass\n"})
    discovery = autodiscovery.RuntimeAutoDiscovery(
        lambda obj: isinstance(obj, type) and obj.__name__ == "C", root
    )

    assert list(discovery) == list(discovery) != []


def test_runtime_include_reaches_nested_files(make_package: MakePackage):
    root = make_package(
        "app",
        {
            "models.py": "class M: pass\n",
            "sub/models.py": "class M: pass\n",
            "sub/other.py": "class M: pass\n",
        },
    )
    discovery = autodiscovery.RuntimeAutoDiscovery(
        lambda obj: isinstance(obj, type) and obj.__name__ == "M",
        root,
        include=["models.py"],
    )

    assert sorted(dict(discovery)) == ["app.models.M", "app.sub.models.M"]


def test_static_keys_are_module_qualified(make_package: MakePackage):
    root = make_package(
        "app",
        {
            "base.py": BASE,
            "models.py": "from app.base import Base\nclass A(Base): pass\n",
            "sub/models.py": "from app.base import Base\nclass A(Base): pass\n",
        },
    )
    base = __import__("app.base", fromlist=["Base"]).Base
    discovery = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_child_of(base), root
    )
    result = dict(discovery)

    assert sorted(result) == ["app.models.A", "app.sub.models.A"]
    assert result["app.models.A"] is not result["app.sub.models.A"]


def test_static_is_reiterable(make_package: MakePackage):
    root = make_package("app", {"m.py": "# static: autoload\nX = 1\n"})
    discovery = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_autoload_validator(), root
    )
    first = list(discovery)

    assert first
    assert list(discovery) == first
    assert list(discovery.load()) == first


def test_static_orders_by_dependency(make_package: MakePackage):
    root = make_package(
        "app",
        {
            "a.py": "# static: autoload\n",
            "b.py": "# static: autoload\nimport app.a\n",
            "c.py": "# static: autoload\nimport app.b\n",
        },
    )
    discovery = autodiscovery.StaticAutoDiscovery(
        autodiscovery.static_autoload_validator(), root
    )

    assert [name for name, _ in discovery] == ["app.a", "app.b", "app.c"]
