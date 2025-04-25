.PHONY: build-dev312 build-dev313 build-test test

venv12_bin := "$(shell pwd)/.venv12"
venv13_bin := "$(shell pwd)/.venv13"

build-dev312:
	@VIRTUAL_ENV="${venv12_bin}" maturin develop -Epydantic,msgspec,sqlalchemy
	@${venv12_bin}/bin/pip install -r dev-requirements.txt

build-dev313:
	@VIRTUAL_ENV="${venv13_bin}" maturin develop -Epydantic,msgspec,sqlalchemy
	@${venv13_bin}/bin/pip install -r dev-requirements.txt

test:
	@${venv12_bin}/bin/pytest
	@${venv13_bin}/bin/pytest

build-test: build-dev312 build-dev313 test
