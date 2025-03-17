import pytest

from escudeiro.url.netloc import Netloc


def test_netloc():  # sourcery skip: extract-duplicate-method
    # Test basic netloc
    netloc = Netloc("www.example.com")
    assert netloc.encode() == "www.example.com"
    assert netloc.host == "www.example.com"
    assert netloc.username is None
    assert netloc.password is None
    assert netloc.port is None

    # Test netloc with port
    netloc = Netloc("www.example.com:8080")
    assert netloc.encode() == "www.example.com:8080"
    assert netloc.host == "www.example.com"
    assert netloc.username is None
    assert netloc.password is None
    assert netloc.port == 8080

    # Test netloc with username and password
    netloc = Netloc("username:password@www.example.com")
    assert netloc.encode() == "username:password@www.example.com"
    assert netloc.host == "www.example.com"
    assert netloc.username == "username"
    assert netloc.password == "password"
    assert netloc.port is None

    # Test netloc from args
    netloc = Netloc.from_args(
        host="www.example.com",
        username="username",
        password="password",
    )
    assert netloc == "username:password@www.example.com"
    assert netloc.host == "www.example.com"
    assert netloc.username == "username"
    assert netloc.password == "password"
    assert netloc.port is None

    # Test merging works

    instance = Netloc("www.example.com")

    assert (
        instance.merge(
            Netloc.from_args(
                host="www.example2.com",
                username="username",
                password="password",
            )
        )
        == "username:password@www.example2.com"
    )
    assert (
        instance.merge_left(
            Netloc.from_args(
                host="www.example2.com",
                username="username",
                password="password",
            )
        )
        == "username:password@www.example.com"
    )


def test_netloc_does_bounds_check_for_port():
    with pytest.raises(ValueError) as exc_info:
        _ = Netloc("www.example.com:66000").encode()

    assert (
        exc_info.value.args[0] == "Invalid port received while parsing netloc."
    )

    netloc = Netloc("example.com")
    with pytest.raises(ValueError) as exc_info:
        netloc.port = 66000

    assert exc_info.value.args[0] == "Received invalid port value."

    netloc = Netloc("example.com")
    with pytest.raises(ValueError) as exc_info:
        netloc.port = -1

    assert exc_info.value.args[0] == "Received invalid port value."
