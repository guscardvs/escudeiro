import os
import shlex
import shutil
import subprocess
import zipfile
from pathlib import Path


def maturin(*args: str):
    _ = subprocess.call(["maturin", *list(args)])


ROOT_DIR = Path(__file__).parent.parent


def build():
    build_dir = ROOT_DIR.joinpath("build")
    build_dir.mkdir(parents=True, exist_ok=True)

    wheels_dir = ROOT_DIR.joinpath("target/wheels")
    if wheels_dir.exists():
        shutil.rmtree(wheels_dir)

    cargo_args = []
    if os.getenv("MATURIN_BUILD_ARGS"):
        cargo_args = shlex.split(os.getenv("MATURIN_BUILD_ARGS", ""))

    maturin("build", "-r", *cargo_args)

    # We won't use the wheel built by maturin directly since
    # we want Poetry to build it but, we need to retrieve the
    # compiled extensions from the maturin wheel.
    wheel = next(iter(wheels_dir.glob("*.whl")))
    with zipfile.ZipFile(wheel.as_posix()) as whl:
        whl.extractall(wheels_dir.as_posix())

        for extension in wheels_dir.rglob("**/*.so"):
            _ = shutil.copyfile(extension, ROOT_DIR.joinpath(extension.name))

    shutil.rmtree(wheels_dir)


if __name__ == "__main__":
    build()
