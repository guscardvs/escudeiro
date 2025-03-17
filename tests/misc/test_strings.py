from escudeiro.misc import strings


def test_to_snake():
    assert strings.to_snake("CamelCase") == "camel_case"
    assert strings.to_snake("camelCase") == "camel_case"
    assert strings.to_snake("camel case") == "camel_case"
    assert strings.to_snake("camel_case") == "camel_case"
    assert strings.to_snake("camel-case") == "camel_case"


def test_to_camel():
    assert strings.to_camel("camel_case") == "camelCase"
    assert strings.to_camel("camelCase") == "camelCase"
    assert strings.to_camel("camel case") == "camelCase"
    assert strings.to_camel("camel_case_") == "camelCase"
    assert strings.to_camel("camel-case") == "camelCase"
    assert strings.to_camel("CamelCase") == "camelCase"


def test_to_pascal():
    assert strings.to_pascal("camel_case") == "CamelCase"
    assert strings.to_pascal("camelCase") == "CamelCase"
    assert strings.to_pascal("camel case") == "CamelCase"
    assert strings.to_pascal("camel_case_") == "CamelCase"
    assert strings.to_pascal("camel-case") == "CamelCase"
    assert strings.to_pascal("CamelCase") == "CamelCase"


def test_to_kebab():
    assert strings.to_kebab("camel_case") == "camel-case"
    assert strings.to_kebab("camelCase") == "camel-case"
    assert strings.to_kebab("camel case") == "camel-case"
    assert (
        strings.to_kebab("camel_case_", remove_trailing_underscores=True)
        == "camel-case"
    )
    assert strings.to_kebab("camel-case") == "camel-case"
    assert strings.to_kebab("CamelCase") == "camel-case"


def test_make_lex_separator():
    print(strings.comma_separator("a,b,c"))
    assert strings.make_lex_separator(tuple, str)("a,b,c") == ("a", "b", "c")
    assert strings.make_lex_separator(list, str)("a,b,c") == ["a", "b", "c"]
    assert strings.make_lex_separator(set, str)("a,b,c") == {"a", "b", "c"}

    assert strings.make_lex_separator(tuple, int)("1,2,3") == (1, 2, 3)
    assert strings.make_lex_separator(list, int)("1,2,3") == [1, 2, 3]
    assert strings.make_lex_separator(set, int)("1,2,3") == {1, 2, 3}

    assert strings.make_lex_separator(tuple, float)("1.1,2.2,3.3") == (
        1.1,
        2.2,
        3.3,
    )
    assert strings.make_lex_separator(list, float)("1.1,2.2,3.3") == [
        1.1,
        2.2,
        3.3,
    ]
    assert strings.make_lex_separator(set, float)("1.1,2.2,3.3") == {
        1.1,
        2.2,
        3.3,
    }


def test_quote():
    assert strings.wrap("foo", "'") == "'foo'"
    assert strings.wrap("foo", '"') == '"foo"'
    assert strings.squote("foo") == "'foo'"
    assert strings.dquote("foo") == '"foo"'


def test_convert():
    assert strings.convert({"foo": "bar"}, strings.to_snake) == {"foo": "bar"}
    assert strings.convert({"foo": "bar"}, strings.to_camel) == {"foo": "bar"}
    assert strings.convert({"foo": "bar"}, strings.to_pascal) == {"Foo": "bar"}
    assert strings.convert({"foo": "bar"}, strings.to_kebab) == {"foo": "bar"}


def test_convert_all():
    assert strings.convert_all({"foo": "bar"}, strings.to_snake) == {
        "foo": "bar"
    }
    assert strings.convert_all({"foo": "bar"}, strings.to_camel) == {
        "foo": "bar"
    }
    assert strings.convert_all({"foo": {"bar": "baz"}}, strings.to_pascal) == {
        "Foo": {"Bar": "baz"}
    }
    assert strings.convert_all({"foo": "bar"}, strings.to_kebab) == {
        "foo": "bar"
    }


def test_comma_separator():
    assert strings.comma_separator("Hello world") == ("Hello world",)
    assert strings.comma_separator("Hello,world") == ("Hello", "world")
    assert strings.comma_separator("Hello, world") == ("Hello", "world")
    assert strings.comma_separator("Hello, world,") == ("Hello", "world")


def test_sentence():
    assert strings.sentence("Hello world") == "Hello world."
    assert strings.sentence("Hello world.") == "Hello world."
    assert strings.sentence("Hello world?") == "Hello world."
    assert strings.sentence("Hello world!") == "Hello world."


def test_exclamation():
    assert strings.exclamation("Hello world") == "Hello world!"
    assert strings.exclamation("Hello world.") == "Hello world!"
    assert strings.exclamation("Hello world?") == "Hello world!"
    assert strings.exclamation("Hello world!") == "Hello world!"


def test_question():
    assert strings.question("Hello world") == "Hello world?"
    assert strings.question("Hello world.") == "Hello world?"
    assert strings.question("Hello world?") == "Hello world?"
    assert strings.question("Hello world!") == "Hello world?"
