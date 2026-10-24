"""In-place edits through URL parts, and copy/aliasing independence."""

import pytest

from escudeiro.url import URL, Fragment, Netloc, Path, Query

BASE = "https://x.com:8080/a/b?c=1#frag"


def test_query_edit_is_visible_on_url():
    url = URL(BASE)
    url.query.add(d="2")
    assert url.encode() == "https://x.com:8080/a/b?c=1&d=2#frag"
    url.query.set(e="3")
    assert url.encode() == "https://x.com:8080/a/b?e=3#frag"
    url.query.remove("e")
    assert url.encode() == "https://x.com:8080/a/b#frag"


def test_path_edit_is_visible_on_url():
    url = URL(BASE)
    url.path.add("c")
    assert url.encode() == "https://x.com:8080/a/b/c?c=1#frag"
    url.path.set("/z")
    assert url.encode() == "https://x.com:8080/z?c=1#frag"
    url.path.add("../y").normalize()
    assert url.encode() == "https://x.com:8080/y?c=1#frag"


def test_netloc_edit_is_visible_on_url():
    url = URL(BASE)
    url.netloc.port = 9
    assert url.encode() == "https://x.com:9/a/b?c=1#frag"
    url.netloc.set(host="y.com")
    assert url.encode() == "https://y.com:9/a/b?c=1#frag"


def test_fragment_edit_is_visible_on_url():
    url = URL(BASE)
    url.fragment.set("other")
    assert url.encode() == "https://x.com:8080/a/b?c=1#other"


def test_part_handles_share_the_url_state():
    url = URL(BASE)
    query = url.query
    url.query.add(d="2")
    assert query.params == {"c": ["1"], "d": ["2"]}
    url.set(query={"z": "9"})
    assert query.params == {"z": ["9"]}


def test_setting_a_part_stores_a_copy():
    one, two = URL("https://a.com/x?k=1"), URL("https://b.com/y")
    two.query = one.query
    two.path = one.path
    two.netloc = one.netloc
    two.fragment = Fragment("f")
    one.query.add(k2="2")
    one.path.add("more")
    one.netloc.port = 1
    assert two.encode() == "https://a.com/x?k=1#f"
    two.query.add(only="two")
    assert one.query.params == {"k": ["1"], "k2": ["2"]}
    assert one.encode() == "https://a.com:1/x/more?k=1&k2=2"


def test_standalone_part_is_not_aliased_when_assigned():
    query = Query("a=1")
    url = URL("https://x.com")
    url.query = query
    query.add(b="2")
    assert url.encode() == "https://x.com?a=1"
    path = Path("/p")
    url.path = path
    path.add("q")
    assert url.encode() == "https://x.com/p?a=1"


def test_copy_is_independent():
    url = URL(BASE)
    other = url.copy()
    other.query.add(d="2")
    other.path.add("c")
    other.netloc.port = 1
    other.fragment.set("new")
    other.scheme = "http"
    assert url.encode() == BASE
    assert other.encode() == "http://x.com:1/a/b/c?c=1&d=2#new"
    url.query.add(only="orig")
    assert "only" not in other.encode()


def test_copy_add_and_copy_set_do_not_touch_original():
    url = URL(BASE)
    added = url.copy_add(path="c", query={"d": "2"}, fragment="f")
    replaced = url.copy_set(path="/z", query={"q": "1"}, netloc="y.com")
    assert url.encode() == BASE
    assert added.encode() == "https://x.com:8080/a/b/c?c=1&d=2#f"
    assert replaced.encode() == "https://y.com/z?q=1#frag"
    assert added is not url
    assert replaced.query is not url.query


def test_url_is_mutable_and_unhashable():
    with pytest.raises(TypeError):
        hash(URL(BASE))


def test_url_in_place_add_and_set_return_self():
    url = URL(BASE)
    assert url.add(path="c") is url
    assert url.set(fragment="f") is url


def test_netloc_object_is_copied_into_url():
    netloc = Netloc("h.com")
    url = URL("https://x.com/p").add(netloc_obj=netloc)
    netloc.port = 5
    assert url.encode() == "https://h.com/p"
    url2 = URL("https://x.com/p").set(netloc_obj=netloc)
    netloc.port = 6
    assert url2.encode() == "https://h.com:5/p"


def test_url_equality_compares_parts_by_value():
    assert URL(BASE) == URL(BASE)
    assert URL(BASE) == BASE
    assert URL(BASE) != URL(BASE).copy_add(path="c")
    url = URL(BASE)
    assert url == url.copy()


def test_path_accepts_pathlib():
    import pathlib

    assert (
        URL("https://x.com/a")
        .add(path="b")
        .path.add(pathlib.PurePosixPath("c/d"))
        .encode()
        == "/a/b/c/d"
    )
