.PHONY: build test

build:
	@poetry install

test:
	@poetry install
	@poetry run pytest
