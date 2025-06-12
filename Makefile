.PHONY: test setup

setup:
	uv sync --all-extras

test:
	@tox p

musllinux-clean:
	@rm -rf ./musllinux/target
	@mkdir -p ./musllinux/target

musllinux-build: musllinux-clean
	docker build -f ./docker/musllinux.dockerfile --build-arg PYVER=3.12 -t escudeiro-musllinux:3.12 .
	docker run --rm -v $(PWD)/musllinux/target:/musllinux/target escudeiro-musllinux:3.12
	docker build -f ./docker/musllinux.dockerfile --build-arg PYVER=3.13 -t escudeiro-musllinux:3.13 .
	docker run --rm -v $(PWD)/musllinux/target:/musllinux/target escudeiro-musllinux:3.13

clean:
	@rm -rf ./target

build: clean musllinux-build
	@bash ./build.sh
