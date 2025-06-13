# String Utilities

The `strings` module provides a collection of utilities for string manipulation, conversion, and parsing. Many of these functions are Rust-backed for performance, making them suitable for high-throughput or large-scale text processing.

---

## Why?

String manipulation is a common need in Python applications, but standard library solutions can be verbose or slow for some use cases. The `strings` module offers concise, efficient, and composable functions for common string transformations, quoting, and parsing tasks.

---

## Features

- **Case conversion**: snake_case, camelCase, PascalCase, kebab-case
- **Sentence formatting**: sentence, exclamation, question
- **Quoting utilities**: single and double quote wrappers
- **Batch replacement**: replace multiple substrings at once
- **Shell-like splitting**: robust comma-separated parsing
- **Dictionary key conversion**: apply formatters to dict keys (recursively)
- **Comment stripping**: remove comments from strings
- **Rust-backed**: many functions are implemented in Rust for speed

---

## Usage

### Case Conversion

```python
from escudeiro.misc.strings import to_snake, to_camel, to_pascal, to_kebab

print(to_snake("MyValue"))    # "my_value"
print(to_camel("my_value"))   # "myValue"
print(to_pascal("my_value"))  # "MyValue"
print(to_kebab("my_value"))   # "my-value"
```

### Sentence and Punctuation Formatting

```python
from escudeiro.misc.strings import sentence, exclamation, question

print(sentence("hello world"))    # "Hello world."
print(exclamation("wow"))         # "Wow!"
print(question("ready"))          # "Ready?"
```

### Quoting

```python
from escudeiro.misc.strings import dquote, squote, wrap

print(dquote("hello"))        # '"hello"'
print(squote("hello"))        # "'hello'"
print(wrap("hello", "*"))     # '*hello*'
```

### Batch Replacement

```python
from escudeiro.misc.strings import replace_all, replace_by

print(replace_all("foo bar baz", {"foo": "x", "baz": "y"}))  # "x bar y"
print(replace_by("a,b;c", "-", {",", ";"}))                  # "a-b-c"
```

### Shell-like Splitting

```python
from escudeiro.misc.strings import comma_separator

print(comma_separator('a, "b, c", d'))  # ('a', 'b, c', 'd')
```

### Dictionary Key Conversion

```python
from escudeiro.misc.strings import convert, convert_all, to_snake

data = {"MyKey": 1, "AnotherKey": {"InnerKey": 2}}
print(convert(data, to_snake))      # {'my_key': 1, 'another_key': {'InnerKey': 2}}
print(convert_all(data, to_snake))  # {'my_key': 1, 'another_key': {'inner_key': 2}}
```

### Comment Stripping

```python
from escudeiro.misc.strings import strip_comment

print(strip_comment('value # this is a comment'))  # "value"
print(strip_comment('"value # not a comment"'))    # '"value # not a comment"'
```

---

## API Reference

### Case Conversion

- `to_snake(value: str) -> str`: Converts to `snake_case`.
- `to_camel(value: str) -> str`: Converts to `camelCase`.
- `to_pascal(value: str) -> str`: Converts to `PascalCase`.
- `to_kebab(value: str, remove_trailing_underscores: bool = True) -> str`: Converts to `kebab-case`.

### Sentence and Punctuation

- `sentence(value: str) -> str`: Formats as a sentence.
- `exclamation(value: str) -> str`: Formats as an exclamation.
- `question(value: str) -> str`: Formats as a question.

### Quoting

- `dquote(value: str) -> str`: Wraps in double quotes.
- `squote(value: str) -> str`: Wraps in single quotes.
- `wrap(value: str, wrapper_char: str) -> str`: Wraps with any character.

### Replacement

- `replace_all(value: str, replacements: Mapping[str, str]) -> str`: Replace multiple substrings.
- `replace_by(value: str, replacement: str, to_replace: Collection[str]) -> str`: Replace all occurrences of substrings with a given string.

### Splitting

- `make_lex_separator(outer_cast, cast=str) -> Callable[[str], Collection]`: Returns a shell-like splitter.
- `comma_separator(value: str) -> tuple[str, ...]`: Splits a comma-separated string, respecting quotes.

### Dictionary Key Conversion

- `convert(value: dict, formatter: Callable[[str], str]) -> dict`: Applies formatter to dict keys.
- `convert_all(value: dict, formatter: Callable[[str], str]) -> dict`: Recursively applies formatter to all dict keys.

### Comment and Quote Handling

- `closing_quote_position(value: str) -> int | None`: Finds the closing quote position if present.
- `strip_comment(value: str, closing_quote: int | None = None) -> str`: Removes comments from a string.

---

## Notes

- Much of this module is Rust-backed for performance.
- Use `convert_all` for deeply nested dictionaries.
- `comma_separator` is robust to quoted values and whitespace.
- Comment stripping only removes comments starting with `#` preceded by a space or tab.

---

## See Also

- [shlex](https://docs.python.org/3/library/shlex.html)
- [Python string methods](https://docs.python.org/3/library/stdtypes.html#string-methods)
- [Rust Python bindings (PyO3)](https://pyo3.rs/)