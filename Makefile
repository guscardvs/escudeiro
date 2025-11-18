.PHONY: test setup musllinux-build musllinux-clean linux-build windows-build build clean post-install-cleanup

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

clean: musllinux-clean
	@rm -rf ./target

post-install-cleanup:
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.pyc' -delete
	@find . -type f -name '*.pyo' -delete
	@rm -rf .eggs/
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info
	@rm -rf .tox/
	@rm -rf .pytest_cache/
	@rm -rf .mypy_cache/
	@find target -type f -name '*-linux*' -delete

linux-build:
	@bash ./build-linux.sh

windows-build:
	@bash ./build-windows.sh

build: clean musllinux-build linux-build windows-build post-install-cleanup
	@echo "All builds are complete. Artifacts are located in the 'target' and 'musllinux' directory."
