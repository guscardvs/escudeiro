"""Parsing, round-tripping and encoding rules."""

import pytest

from escudeiro.url import URL, Fragment, Netloc, Path, Query

ROUND_TRIPS = [
    # absolute
    "https://u:p@x.com:8080/a/b?c=1#frag",
    "https://x.com",
    "https://x.com/",
    "https://x.com/a/b/",
    "redis://localhost:6379/0",
    "https://x.com/#/home",
    "https://x.com/#a%20b",
    "https://us%40er@x.com/",
    "https://x.com:443/",
    "http://x.com:80/",
    "https://[::1]:8080/x",
    "file:///tmp/x",
    # relative references
    "/a/b?c=1",
    "example.com/x",
    "a/b/",
    "../up/x",
    "//cdn.x.com/lib.js",
    "?a=1",
    "#top",
    "",
    # opaque
    "mailto:a@b.com",
    "tel:+1-555-0100",
    "data:text/plain;base64,SGk=",
]


@pytest.mark.parametrize("raw", ROUND_TRIPS)
def test_encode_round_trips(raw: str):
    assert URL(raw).encode() == raw
    assert URL(URL(raw).encode()).encode() == raw


def test_relative_and_opaque_parts():
    url = URL("/a/b?c=1")
    assert url.scheme == ""
    assert url.netloc.host == ""
    assert url.path.encode() == "/a/b"
    assert url.query.params == {"c": ["1"]}

    url = URL("mailto:a@b.com")
    assert url.scheme == "mailto"
    assert url.path.encode() == "a@b.com"
    assert url.netloc.encode() == ""


def test_scheme_is_lowercased_and_host_normalized():
    assert URL("HTTPS://Example.COM/X").encode() == "https://example.com/X"


@pytest.mark.parametrize(
    "raw",
    ["http://[bad", "http://x.com:99999", "http://exa mple.com/", "http://x:y"],
)
def test_invalid_urls_raise(raw: str):
    with pytest.raises(ValueError):
        URL(raw)


def test_invalid_netloc_raises():
    with pytest.raises(ValueError):
        Netloc("a b")
    with pytest.raises(ValueError):
        Netloc("[bad")
    with pytest.raises(ValueError):
        Netloc("x.com:99999")
    with pytest.raises(ValueError):
        Netloc("example.com").parse("a b")
    with pytest.raises(ValueError):
        Netloc.from_args("a b")


def test_netloc_parse_failure_leaves_instance_unchanged():
    netloc = Netloc("x.com:80")
    with pytest.raises(ValueError):
        netloc.parse("y.com:99999")
    assert netloc.encode() == "x.com:80"


def test_url_set_and_add_netloc_errors_propagate():
    for method in ("add", "set"):
        url = URL("https://x.com/p")
        with pytest.raises(ValueError):
            getattr(url, method)(netloc="y.com:99999")
        assert url.encode() == "https://x.com/p"
        with pytest.raises(ValueError):
            getattr(url, method)(netloc="a b")


def test_default_ports_are_kept_consistently():
    assert Netloc("example.com:443").port == 443
    assert Netloc("example.com:80").port == 80
    assert URL("https://example.com:443/x").netloc.port == 443


def test_netloc_userinfo_is_encoded_once():
    assert Netloc("us%40er@x.com").encode() == "us%40er@x.com"
    assert Netloc("us%40er:p%3Aw@x.com").encode() == "us%40er:p%3Aw@x.com"
    netloc = Netloc.from_args("x.com", username="us@er", password="p w")
    assert netloc.encode() == "us%40er:p%20w@x.com"
    assert Netloc(netloc.encode()).encode() == netloc.encode()
    assert netloc.set(username="a/b").encode() == "a%2Fb:p%20w@x.com"


def test_path_does_not_go_through_url_parsing():
    assert Path("/a/b").add("../c").segments == ["", "a", "b", "..", "c"]
    assert Path("/a/b").add("../c").normalize().encode() == "/a/c"
    assert Path("/a").add("f?x=1").encode() == "/a/f%3Fx=1"
    assert Path("/a").add("f#1").encode() == "/a/f%231"
    assert Path("file#1.txt").encode() == "file%231.txt"
    assert Path("a b").encode() == "a%20b"
    assert Path("a%20b/%zz").encode() == "a%20b/%25zz"
    assert Path("/café").encode() == "/caf%C3%A9"


def test_path_collapses_every_duplicate_slash():
    assert Path("a//b/c").encode() == "a/b/c"
    assert Path("/a//b///c//").encode() == "/a/b/c/"


def test_relative_path_stays_relative():
    path = Path("a/b")
    assert path.segments == ["a", "b"]
    assert path.encode() == "a/b"
    assert path.add("c").encode() == "a/b/c"
    assert Path("a/./b/../c").normalize().encode() == "a/c"
    assert Path("../a/../..").normalize().encode() == "../.."


def test_add_path_to_url_without_path_adds_leading_slash():
    assert URL("https://x.com").add(path="p").encode() == "https://x.com/p"


def test_fragment_is_encoded_once():
    assert Fragment("/home").encode() == "/home"
    assert Fragment("a%20b").encode() == "a%20b"
    assert Fragment("a b").encode() == "a%20b"
    assert Fragment("x").set("a b").encode() == "a%20b"
    assert Fragment("x").set("a b").encode() == Fragment("a b").encode()
    assert Fragment("x").set("a%20b").encode() == "a%20b"
    assert Fragment("x").set("#/h?q").encode() == "%23/h?q"
    assert URL("https://x.com").add(fragment="a b").encode() == (
        "https://x.com#a%20b"
    )


def test_query_keeps_insertion_order():
    assert Query("b=1&a=2&z=3").encode() == "b=1&a=2&z=3"
    assert list(Query("b=1&a=2&z=3").params) == ["b", "a", "z"]
    assert URL("https://x.com/?b=1&a=2&z=3").encode() == (
        "https://x.com/?b=1&a=2&z=3"
    )
    assert Query("b=1").add({"a": "2", "c": "3"}).encode() == "b=1&a=2&c=3"
    assert Query("b=1&a=2").first() == {"b": "1", "a": "2"}
    assert list(Query("b=1&a=2").first()) == ["b", "a"]


def test_query_sort():
    query = Query("b=1&a=2&b=0&a=1").sort()
    assert query.encode() == "a=2&a=1&b=1&b=0"


def test_query_set_merges_mapping_and_kwargs():
    query = Query("x=1&y=2").set({"a": "1"}, b="2")
    assert query.params == {"a": ["1"], "b": ["2"]}
    assert Query("x=1").set(a="1").params == {"a": ["1"]}
    assert Query("x=1").set({}).params == {}


def test_query_setitem_replaces_and_getitem_defaults():
    query = Query("a=1&a=2&b=3")
    query["a"] = "9"
    assert query.params == {"a": ["9"], "b": ["3"]}
    assert query.encode() == "a=9&b=3"
    query["new"] = "n"
    assert query.encode() == "a=9&b=3&new=n"
    assert query["missing"] == []
    assert query["b"] == ["3"]


def test_query_equality_ignores_order_of_keys():
    assert Query("a=1&b=2") == Query("b=2&a=1")
    assert Query("a=1") != Query("a=2")


def test_url_from_netloc_builds_from_components():
    url = URL.from_netloc(host="example.com", port=8080)
    assert url.encode() == "//example.com:8080"
    assert url.netloc.host == "example.com"
    assert url.netloc.port == 8080
    assert url.set(scheme="https", path="/x").encode() == (
        "https://example.com:8080/x"
    )

    url = URL.from_netloc(Netloc("a.com:1"), username="u", password="p", port=2)
    assert url.encode() == "//u:p@a.com:2"
    assert URL.from_netloc(Netloc("a.com:1")).encode() == "//a.com:1"
    assert URL.from_netloc().encode() == ""


def test_url_from_args():
    url = URL.from_args(
        path="/a",
        query={"k": "v"},
        fragment="f",
        netloc="x.com",
        scheme="https",
    )
    assert url.encode() == "https://x.com/a?k=v#f"
