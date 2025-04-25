.PHONY: test setup

setup:
	bash ./setup-venv.sh

test:
	@tox p
