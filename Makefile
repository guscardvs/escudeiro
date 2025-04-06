.PHONY: build-dev test

venv_bin := "$(shell pwd)/.venv/bin"


build-dev:
	@maturin develop -Epydantic,msgspec
	@${venv_bin}/pip install -r dev-requirements.txt

test: build-dev
	@${venv_bin}/pytest
