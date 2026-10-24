import itertools
import sys
import textwrap
import types
from collections.abc import Callable, Iterator

import pytest

_counter = itertools.count()


@pytest.fixture
def load_module() -> Iterator[Callable[[str], types.ModuleType]]:
    """Execute `source` as a real, importable module.

    `update_refs` and the generated methods resolve names through
    `sys.modules[cls.__module__]`, so locally defined classes would not do."""
    names: list[str] = []

    def load(source: str) -> types.ModuleType:
        name = f"squire_dynamic_module_{next(_counter)}"
        module = types.ModuleType(name)
        sys.modules[name] = module
        names.append(name)
        code = compile(textwrap.dedent(source), f"<{name}>", "exec")
        exec(code, module.__dict__)
        return module

    yield load
    for name in names:
        _ = sys.modules.pop(name, None)
