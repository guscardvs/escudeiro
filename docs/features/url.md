# URL Utilities

The `url` module in `escudeiro` provides a modern, object-oriented interface for parsing, constructing, and manipulating URLs. It supports all standard URL components and offers a fluent, immutable API for safe and expressive URL handling.

---

## Why?

Manipulating URLs with the Python standard library can be verbose and error-prone:

```python
from urllib.parse import urlparse, urlunparse

parsed = urlparse("https://user:pass@host:8080/path?query=1#frag")
new_url = urlunparse(parsed._replace(path="/newpath"))
```

With `escudeiro.url`, you get a high-level, immutable `URL` object with convenient accessors and modifiers:

```python
from escudeiro.url import URL

url = URL("https://user:pass@host:8080/path?query=1#frag")
print(url.path)  # "/path"
new_url = url.add(path="newpath")
print(str(new_url))  # "https://user:pass@host:8080/path/newpath?query=1#frag"
```

---

## Features

- **Full URL parsing and construction** (scheme, userinfo, host, port, path, query, fragment)
- **Immutable, chainable API** for safe modifications
- **Component-wise access and modification** via `.add()` and properties
- **Convenient helpers** for query, path, fragment, and netloc manipulation
- **Type-safe and dataclass-friendly**

---

## Usage

### Adding Query Parameters

```python
from escudeiro.url import URL

url = URL("https://www.example.com/path?key1=value1").add(
    query={"key2": "value2", "key3": "value3"}
)
print(url.query)  # "key1=value1&key2=value2&key3=value3"
print(str(url))   # "https://www.example.com/path?key1=value1&key2=value2&key3=value3"
```

### Adding Path Segments

```python
url = URL("https://www.example.com/path").add(path="subpath")
print(url.path)  # "/path/subpath"
print(str(url))  # "https://www.example.com/path/subpath"
```

### Adding a Fragment

```python
url = URL("https://www.example.com/path").add(fragment="section1")
print(url.fragment)  # "section1"
print(str(url))      # "https://www.example.com/path#section1"
```

### Modifying Netloc (Host, Userinfo, Port)

```python
from escudeiro.url import Netloc

url = URL("https://www.example.com/path").add(netloc="www.example2.com")
print(url.netloc)  # "www.example2.com"
print(str(url))    # "https://www.example2.com/path"

url = URL("https://www.example.com/path").add(
    netloc_obj=Netloc.from_args(
        host="www.example2.com",
        username="username",
        password="password",
    )
)
print(url.netloc)  # "username:password@www.example2.com"
print(str(url))    # "https://username:password@www.example2.com/path"

url = URL("https://www.example.com/path").add(
    netloc_obj=Netloc.from_args(host="www.example2.com", port=8080)
)
print(url.netloc)  # "www.example2.com:8080"
print(str(url))    # "https://www.example2.com:8080/path"
```

### Composing Multiple Components

```python
url = URL("https://www.example.com/path?key1=value1").add(
    path="subpath",
    query={"key2": "value2", "key3": "value3"},
    fragment="section1",
    netloc_obj=Netloc.from_args(
        host="www.example2.com",
    username="username",
    password="password",
    port=8080,
        )
    )
    print(url.path)      # "/path/subpath"
    print(url.query)     # "key1=value1&key2=value2&key3=value3"
    print(url.fragment)  # "section1"
    print(url.netloc)    # "username:password@www.example2.com:8080"
    print(str(url))
    # "https://username:password@www.example2.com:8080/path/subpath?key1=value1&key2=value2&key3=value3#section1"
```

---

## Immutability and Copying

All operations on `URL` objects return new instances. You can safely copy and compare URLs:

```python
url = URL("https://www.example.com/path?key1=value1").add(
    query={"key2": "value2", "key3": "value3"}
)
url2 = url.copy()
assert url2 is not url
assert url2 == url
```

---

## API Reference

### `URL` class

- **Construction:** `URL(str_or_url)`
- **Properties:** `.scheme`, `.netloc`, `.path`, `.query`, `.fragment`
- **Methods:**
    - `.add(...)`: Return a new URL with updated components (`path`, `query`, `fragment`, `netloc`, `netloc_obj`)
    - `.copy()`: Return a new identical URL instance
    - `.encode()`: Return the URL as a string
    - `.from_args(...)` Return a new URL from the args received. Shortcut to `URL("").set(...)`

### `Netloc`, `Path`, `Query`, `Fragment`

- Helper classes for manipulating respective URL components.
- `Netloc.from_args(host, username=None, password=None, port=None)`: Construct a netloc string from components.
- `Path`, `Query`, and `Fragment` can be used similarly for their respective components.
---

## Notes

- All modifications are immutable and chainable.
- Query parameters can be provided as dicts or strings.
- Use `netloc_obj` for advanced netloc construction (user, password, port).
- The API is type-safe and works well with dataclasses.

---

## See Also

- [Python `urllib.parse`](https://docs.python.org/3/library/urllib.parse.html)
- [escudeiro.url source code](https://github.com/cardoso/escudeiro/tree/develop/escudeiro/url)
