.PHONY: test setup

setup:
	bash ./setup-venv.sh

test:
	@tox p

clean:
	@rm -rf ./target

build: clean
	@bash ./build.sh

