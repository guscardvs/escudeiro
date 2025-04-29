#!/bin/bash

if ! [ -d ./.venv ]; then
    echo "Creating .venv with python3.12 from hatch"

    virtualenv --py $(hatch python find 3.12) .venv
fi

extras=$(./.venv/bin/python -c '
import tomllib
with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
    deps = data.get("project", {}).get("optional-dependencies", {})
    print(",".join(deps.keys()))
')

if ! command -v maturin; then
    ./.venv/bin/pip install -U pip maturin
    ./.venv/bin/maturin develop -E${extras}
else
    maturin develop -E${extras}
fi
