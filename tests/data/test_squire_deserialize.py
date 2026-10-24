"""Regression tests for squire.deserialize (src/squire.rs)."""

import subprocess
import sys
import textwrap

import pytest

from escudeiro.escudeiro_pyrs import squire


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_deep_list_raises_recursion_error_instead_of_aborting():
    result = _run(
        """
        from escudeiro.escudeiro_pyrs import squire

        value = []
        for _ in range(20000):
            value = [value]
        try:
            squire.deserialize(value)
        except RecursionError:
            print("recursion-error")
        """
    )
    # an interpreter abort would give a negative return code (signal)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "recursion-error"


@pytest.mark.parametrize(
    "build",
    [
        "value = []; value.append(value)",
        "value = {}; value['a'] = [value]",
        "inner = []; value = (inner,); inner.append(value)",
    ],
)
def test_cyclic_input_is_rejected_without_aborting(build: str):
    result = _run(
        f"""
        from escudeiro.escudeiro_pyrs import squire

        {build}
        try:
            squire.deserialize(value)
        except ValueError as err:
            print("cycle:", err)
        """
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("cycle:")


def test_moderate_nesting_still_works():
    value = []
    for _ in range(400):
        value = [value]
    assert squire.deserialize(value) == value


def test_shared_but_acyclic_references_are_fine():
    shared = [1, 2]
    assert squire.deserialize({"a": shared, "b": shared}) == {
        "a": [1, 2],
        "b": [1, 2],
    }


def test_iterator_errors_are_propagated_not_panics():
    class Boom(Exception):
        pass

    class Items(list):
        def __iter__(self):
            yield 1
            raise Boom

    with pytest.raises(Boom):
        squire.deserialize(Items([1]))


def test_set_items_are_deserialized():
    class Hashable:
        def __parse_dict__(self, by_alias: bool):
            return "parsed"

    class Unhashable:
        def __parse_dict__(self, by_alias: bool):
            return {"k": 1}

    assert squire.deserialize({Hashable()}) == {"parsed"}
    assert squire.deserialize({Unhashable()}) == [{"k": 1}]
    assert squire.deserialize({1, 2}) == {1, 2}
    assert squire.deserialize((1, [2])) == (1, [2])


def test_by_alias_defaults_to_false():
    class Aliased:
        __squire_attrs__ = {}

        def __parse_dict__(self, by_alias: bool):
            return {"by_alias": by_alias}

    assert squire.deserialize(Aliased()) == {"by_alias": False}
    assert squire.deserialize(Aliased(), True) == {"by_alias": True}
    assert squire.deserialize_mapping({"x": Aliased()}) == {
        "x": {"by_alias": False}
    }
    assert squire.deserialize_mapping({"x": Aliased()}, True) == {
        "x": {"by_alias": True}
    }
