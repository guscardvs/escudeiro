.PHONY: test setup

DOCKER_RUNTIME ?= docker

setup:
	@uv sync --all-extras

test:
	@tox p

musllinux-clean:
	@rm -rf ./musllinux/target
	@mkdir -p ./musllinux/target

musllinux-build: musllinux-clean
	for ver in 3.12 3.13 3.14; do \
		$(DOCKER_RUNTIME) build -f ./docker/musllinux.dockerfile --build-arg PYVER=$$ver -t escudeiro-musllinux:$$ver .; \
		$(DOCKER_RUNTIME) run --rm -v $(PWD)/musllinux/target:/musllinux/target escudeiro-musllinux:$$ver; \
	done
clean:
	@rm -rf ./target

build: clean musllinux-build
	@bash ./build.sh
