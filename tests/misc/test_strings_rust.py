"""Regression tests for the Rust string helpers (src/strings.rs)."""

import pytest

from escudeiro.misc import strings

# Word rule: separators are `_`, `-` and whitespace; a new word also starts at
# an uppercase letter after a lowercase letter or digit, and at the last capital
# of an acronym run followed by a lowercase letter. Digits stay with the word
# before them (so `OAuth2Client` is `O|Auth2|Client`). Leading underscores are
# always preserved; trailing ones too, except that camel/pascal drop them on a
# plain name (`type_` -> `type`, the keyword-escape convention) and kebab drops
# them unless `remove_trailing_underscores=False`.
CASES = [
    # input, snake, camel, pascal, kebab
    ("CamelCase", "camel_case", "camelCase", "CamelCase", "camel-case"),
    ("camel case", "camel_case", "camelCase", "CamelCase", "camel-case"),
    ("HTTPServer", "http_server", "httpServer", "HttpServer", "http-server"),
    (
        "getHTTPResponse",
        "get_http_response",
        "getHttpResponse",
        "GetHttpResponse",
        "get-http-response",
    ),
    (
        "XMLHttpRequest",
        "xml_http_request",
        "xmlHttpRequest",
        "XmlHttpRequest",
        "xml-http-request",
    ),
    (
        "OAuth2Client",
        "o_auth2_client",
        "oAuth2Client",
        "OAuth2Client",
        "o-auth2-client",
    ),
    ("var1Name", "var1_name", "var1Name", "Var1Name", "var1-name"),
    ("item_2_name", "item_2_name", "item2Name", "Item2Name", "item-2-name"),
    ("_private", "_private", "_private", "_Private", "_private"),
    ("__init__", "__init__", "__init__", "__Init__", "__init__"),
    ("ABC", "abc", "abc", "Abc", "abc"),
    # a trailing underscore on a plain name only escapes a keyword
    ("type_", "type_", "type", "Type", "type_"),
    ("camel_case_", "camel_case_", "camelCase", "CamelCase", "camel-case_"),
    ("_x_", "_x_", "_x_", "_X_", "_x_"),
    ("", "", "", "", ""),
]


@pytest.mark.parametrize(("value", "snake", "camel", "pascal", "kebab"), CASES)
def test_case_conversions(
    value: str, snake: str, camel: str, pascal: str, kebab: str
):
    assert strings.to_snake(value) == snake
    assert strings.to_camel(value) == camel
    assert strings.to_pascal(value) == pascal
    assert strings.to_kebab(value, remove_trailing_underscores=False) == kebab


def test_kebab_trailing_underscores():
    assert strings.to_kebab("name_") == "name"
    assert strings.to_kebab("name_", remove_trailing_underscores=False) == (
        "name_"
    )


def test_replace_all_is_deterministic():
    # chained replacements used to depend on hash order (`cc` vs `bc`)
    results = {
        strings.replace_all("ab", {"a": "b", "b": "c"}) for _ in range(300)
    }
    assert results == {"bc"}


def test_replace_all_leftmost_longest_and_literal():
    assert strings.replace_all("abc", {"a": "x", "ab": "y"}) == "yc"
    assert strings.replace_all("a.b*c", {".": "-", "*": "+"}) == "a-b+c"
    assert strings.replace_all("abc", {"": "x"}) == "abc"
    assert strings.replace_all("abc", {}) == "abc"


def test_replace_by_single_pass():
    assert strings.replace_by("a-b c", "_", ["-", " "]) == "a_b_c"
    # replaced text is not rescanned
    assert strings.replace_by("ab", "a", ["a", "b"]) == "aa"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Hello", "Hello."),
        ("Hello.", "Hello."),
        ("Really?!", "Really?!"),
        ("Really?", "Really?"),
        ("Wow!", "Wow!"),
        ("", ""),
    ],
)
def test_sentence(value: str, expected: str):
    assert strings.sentence(value) == expected
