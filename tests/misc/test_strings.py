from escudeiro.misc import strings


class TestStringConversions:
    def test_to_snake(self):
        assert strings.to_snake("CamelCase") == "camel_case"
        assert strings.to_snake("camelCase") == "camel_case"
        assert strings.to_snake("camel case") == "camel_case"
        assert strings.to_snake("camel_case") == "camel_case"
        assert strings.to_snake("camel-case") == "camel_case"

    def test_to_camel(self):
        assert strings.to_camel("camel_case") == "camelCase"
        assert strings.to_camel("camelCase") == "camelCase"
        assert strings.to_camel("camel case") == "camelCase"
        assert strings.to_camel("camel_case_") == "camelCase"
        assert strings.to_camel("camel-case") == "camelCase"
        assert strings.to_camel("CamelCase") == "camelCase"

    def test_to_pascal(self):
        assert strings.to_pascal("camel_case") == "CamelCase"
        assert strings.to_pascal("camelCase") == "CamelCase"
        assert strings.to_pascal("camel case") == "CamelCase"
        assert strings.to_pascal("camel_case_") == "CamelCase"
        assert strings.to_pascal("camel-case") == "CamelCase"
        assert strings.to_pascal("CamelCase") == "CamelCase"

    def test_to_kebab(self):
        assert strings.to_kebab("camel_case") == "camel-case"
        assert strings.to_kebab("camelCase") == "camel-case"
        assert strings.to_kebab("camel case") == "camel-case"
        assert (
            strings.to_kebab("camel_case_", remove_trailing_underscores=True)
            == "camel-case"
        )
        assert strings.to_kebab("camel-case") == "camel-case"
        assert strings.to_kebab("CamelCase") == "camel-case"


class TestMakeLexSeparator:
    def test_make_lex_separator(self):
        assert strings.make_lex_separator(tuple, str)("a,b,c") == (
            "a",
            "b",
            "c",
        )
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


class TestQuote:
    def test_quote(self):
        assert strings.wrap("foo", "'") == "'foo'"
        assert strings.wrap("foo", '"') == '"foo"'
        assert strings.squote("foo") == "'foo'"
        assert strings.dquote("foo") == '"foo"'


class TestConvert:
    def test_convert(self):
        assert strings.convert({"foo": "bar"}, strings.to_snake) == {
            "foo": "bar"
        }
        assert strings.convert({"foo": "bar"}, strings.to_camel) == {
            "foo": "bar"
        }
        assert strings.convert({"foo": "bar"}, strings.to_pascal) == {
            "Foo": "bar"
        }
        assert strings.convert({"foo": "bar"}, strings.to_kebab) == {
            "foo": "bar"
        }

    def test_convert_all(self):
        assert strings.convert_all({"foo": "bar"}, strings.to_snake) == {
            "foo": "bar"
        }
        assert strings.convert_all({"foo": "bar"}, strings.to_camel) == {
            "foo": "bar"
        }
        assert strings.convert_all(
            {"foo": {"bar": "baz"}}, strings.to_pascal
        ) == {"Foo": {"Bar": "baz"}}
        assert strings.convert_all({"foo": "bar"}, strings.to_kebab) == {
            "foo": "bar"
        }


class TestCommaSeparator:
    def test_comma_separator(self):
        assert strings.comma_separator("Hello world") == ("Hello world",)
        assert strings.comma_separator("Hello,world") == ("Hello", "world")
        assert strings.comma_separator("Hello, world") == ("Hello", "world")
        assert strings.comma_separator("Hello, world,") == ("Hello", "world")


class TestSentence:
    def test_sentence(self):
        assert strings.sentence("Hello world") == "Hello world."
        assert strings.sentence("Hello world.") == "Hello world."
        assert strings.sentence("Hello world?") == "Hello world."
        assert strings.sentence("Hello world!") == "Hello world."


class TestExclamation:
    def test_exclamation(self):
        assert strings.exclamation("Hello world") == "Hello world!"
        assert strings.exclamation("Hello world.") == "Hello world!"
        assert strings.exclamation("Hello world?") == "Hello world!"
        assert strings.exclamation("Hello world!") == "Hello world!"


class TestQuestion:
    def test_question(self):
        assert strings.question("Hello world") == "Hello world?"
        assert strings.question("Hello world.") == "Hello world?"
        assert strings.question("Hello world?") == "Hello world?"
        assert strings.question("Hello world!") == "Hello world?"


class TestClosingQuotePosition:
    def test_empty_string(self):
        """Test with an empty string."""
        assert strings.closing_quote_position("") is None

    def test_string_without_quotes(self):
        """Test with a string that doesn't start with quotes."""
        assert strings.closing_quote_position("hello world") is None

    def test_single_quoted_string(self):
        """Test with a string wrapped in single quotes."""
        assert strings.closing_quote_position("'hello world'") == 12

    def test_double_quoted_string(self):
        """Test with a string wrapped in double quotes."""
        assert strings.closing_quote_position('"hello world"') == 12

    def test_unclosed_quote(self):
        """Test with a string that has an opening quote but no closing quote."""
        assert strings.closing_quote_position("'hello world") is None

    def test_escaped_quote(self):
        """Test with a string that has an escaped quote."""
        assert strings.closing_quote_position(r"'hello \'world'") == 14

    def test_quote_in_middle(self):
        """Test with a string that has quotes in the middle but doesn't start with one."""
        assert strings.closing_quote_position("hello 'world'") is None

    def test_multiple_quotes(self):
        """Test with a string that has multiple quotes."""
        assert strings.closing_quote_position("'hello' 'world'") == 6

    def test_just_a_quote(self):
        """Test with a string that is just a quote character."""
        assert strings.closing_quote_position("'") is None
        assert strings.closing_quote_position('"') is None

    def test_two_quotes(self):
        """Test with a string that is just an opening and closing quote."""
        assert strings.closing_quote_position("''") == 1
        assert strings.closing_quote_position('""') == 1


class TestStripComment:
    def test_no_comment(self):
        """Test with a string without comments."""
        assert strings.strip_comment("hello world") == "hello world"

    def test_comment_at_end(self):
        """Test with a string that has a comment at the end."""
        assert strings.strip_comment("hello world # comment") == "hello world"

    def test_tab_before_comment(self):
        """Test with a string that has a tab before the comment."""
        assert strings.strip_comment("hello world\t# comment") == "hello world"

    def test_hash_without_space(self):
        """Test with a string that has a # but without a space before it."""
        assert strings.strip_comment("hello#world") == "hello#world"

    def test_hash_without_space_after(self):
        """Test with a string that has a # but without a space after it."""
        assert strings.strip_comment("hello #comment") == "hello #comment"

    def test_multiple_comments(self):
        """Test with a string that has multiple # characters."""
        assert (
            strings.strip_comment("hello # first comment # second") == "hello"
        )

    def test_empty_string(self):
        """Test with an empty string."""
        assert strings.strip_comment("") == ""

    def test_just_a_comment(self):
        """Test with a string that is just a comment."""
        assert strings.strip_comment("# comment") == ""

    def test_hash_at_start(self):
        """Test with a # at the start of the string."""
        assert strings.strip_comment("# comment") == ""

    def test_hash_at_end(self):
        """Test with a # at the end of the string."""
        assert strings.strip_comment("hello # ") == "hello"

    def test_quoted_hash(self):
        """Test with a string that has a # inside quotes."""
        value = "'hello # not a comment'"
        closing = strings.closing_quote_position(value)
        assert (
            strings.strip_comment(value, closing) == "'hello # not a comment'"
        )

    def test_comment_after_quote(self):
        """Test with a string that has a comment after a quoted section."""
        value = "'hello world' # comment"
        closing = strings.closing_quote_position(value)
        assert strings.strip_comment(value, closing) == "'hello world'"

    def test_fully_quoted_string(self):
        """Test with a string that is fully quoted."""
        value = "'hello world'"
        closing = 12  # Position of the closing quote
        assert strings.strip_comment(value, closing) == "'hello world'"

    def test_quoted_string_with_hash(self):
        """Test with a quoted string containing a hash that's not a comment."""
        value = "'hello # world'"
        closing = strings.closing_quote_position(value)
        assert strings.strip_comment(value, closing) == "'hello # world'"

    def test_hash_with_tab_after(self):
        """Test with a hash followed by a tab."""
        assert strings.strip_comment("hello #\tcomment") == "hello"

    def test_hash_at_end_of_string(self):
        """Test with a hash at the end of the string."""
        assert strings.strip_comment("hello #") == "hello"

    def test_hash_with_multiple_spaces(self):
        """Test with multiple spaces before and after the hash."""
        assert strings.strip_comment("hello   #   comment") == "hello"

    def test_multiple_hashtags(self):
        """Test with multiple hashtags with proper spacing."""
        test_str = "some code # first comment some text # second comment"
        assert strings.strip_comment(test_str) == "some code"

    def test_integration_both_functions(self):
        """Test both functions together for various cases."""
        test_cases = [
            ("'hello world'", "'hello world'"),
            ("'hello world' # comment", "'hello world'"),
            ("hello world # comment", "hello world"),
            ("'hello # not a comment'", "'hello # not a comment'"),
            ("'hello \\'world\\'' # comment", "'hello \\'world\\''"),
            ('"hello # world" # real comment', '"hello # world"'),
            ("code with #no comment", "code with #no comment"),
            ("code with # proper comment", "code with"),
            ("# comment at start", ""),
            (
                "'text # not comment' # real comment",
                "'text # not comment'",
            ),
        ]

        for input_str, expected in test_cases:
            closing = strings.closing_quote_position(input_str)
            assert strings.strip_comment(input_str, closing) == expected


class TestAsBoolean:
    def test_as_boolean(self):
        assert strings.as_boolean("True") is True
        assert strings.as_boolean("true") is True
        assert strings.as_boolean("1") is True
        assert strings.as_boolean("False") is False
        assert strings.as_boolean("false") is False
        assert strings.as_boolean("0") is False
        assert strings.as_boolean("yes") is True
        assert strings.as_boolean("no") is False
        assert strings.as_boolean("") is False
        assert strings.as_boolean("random string") is None


class TestIsNone:
    def test_is_none(self):
        assert strings.is_none("") is True
        assert strings.is_none("None") is True
        assert strings.is_none("none") is True
        assert strings.is_none("null") is True
        assert strings.is_none("NULL") is True
        assert strings.is_none("nil") is True
        assert strings.is_none("NIL") is True
        assert strings.is_none("NaN") is False
        assert strings.is_none("nan") is False
        assert strings.is_none("0") is False
        assert strings.is_none("1") is False
