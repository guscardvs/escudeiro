# JSONX: Fast JSON with orjson

The `jsonx` module is a lightweight wrapper around [orjson](https://github.com/ijl/orjson) that provides a familiar interface similar to Python's built-in `json` module, but with much better performance. It is designed for drop-in usage in projects that want the speed of orjson with the convenience of the standard library.

---

## Why?

Python's built-in `json` module is easy to use but can be slow for large or complex data. `orjson` is one of the fastest JSON libraries for Python, but its API differs from the standard library. The `jsonx` module bridges this gap, offering a nearly identical API to `json` while using `orjson` under the hood.

```python
import jsonx

data = {"foo": 1, "bar": [1, 2, 3]}
s = jsonx.dumps(data)
print(s)  # '{"foo":1,"bar":[1,2,3]}'
```

---

## Features

- **API compatible** with Python's `json` module (`dumps`, `loads`, `dump`, `load`)
- **Much faster** serialization/deserialization via `orjson`
- **Supports custom default encoders**
- **Optional pretty-printing (indentation)**
- **Handles both text and binary file objects**

---

## Usage

### Basic Serialization

```python
import jsonx

obj = {"a": 1, "b": [2, 3]}
s = jsonx.dumps(obj)
print(s)  # '{"a":1,"b":[2,3]}'
```

### Deserialization

```python
import jsonx

s = '{"a":1,"b":[2,3]}'
obj = jsonx.loads(s)
print(obj)  # {'a': 1, 'b': [2, 3]}
```

### File Operations

```python
import jsonx

# Writing to a file
with open("data.json", "wb") as f:
    jsonx.dump({"x": 42}, f, indent=True)

# Reading from a file
with open("data.json", "rb") as f:
    data = jsonx.load(f)
```

### Custom Default Encoder

```python
import jsonx
import datetime

def encode_dt(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError

jsonx.dumps({"now": datetime.datetime.now()}, default=encode_dt)
```

---

## API Reference

### `dumps`

```python
def dumps(
    val: Any,
    *,
    default: Callable[[Any], Any] | None = None,
    option: int | None = None,
) -> str
```
- **Description:** Serialize Python object to a JSON-formatted `str`.
- **Parameters:**
  - `val`: The object to serialize.
  - `default`: Optional function to handle non-serializable objects.
  - `option`: Optional orjson option flags (advanced).
- **Returns:** JSON string.

### `loads`

```python
loads: Callable[[str | bytes | bytearray | memoryview], Any]
```
- **Description:** Deserialize JSON string or bytes to Python object.

### `dump`

```python
def dump(
    obj: Any,
    fdes: BinaryIO,
    *,
    default: Callable[[Any], Any] | None = None,
    indent: bool = False,
) -> None
```
- **Description:** Serialize Python object and write to a binary file.
- **Parameters:**
  - `obj`: The object to serialize.
  - `fdes`: File object opened in binary mode.
  - `default`: Optional encoder for unsupported types.
  - `indent`: Pretty-print with 2-space indentation if `True`.

### `load`

```python
def load(fdes: BinaryIO | TextIO) -> Any
```
- **Description:** Read JSON from a file object and deserialize to Python object.
- **Parameters:**
  - `fdes`: File object (binary or text mode).

---

## Notes

- Always open files in binary mode (`"wb"`/`"rb"`) for best compatibility.
- `jsonx` does not support all options of the built-in `json` module (e.g., `sort_keys`).
- For advanced options, pass `option` to `dumps` using `orjson` flags.

---

## See Also

- [orjson documentation](https://github.com/ijl/orjson)
- [Python built-in json](https://docs.python.org/3/library/json.html)
- [PEP 8: I/O](https://peps.python.org/pep-0008/#input-and-output)