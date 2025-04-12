#!/bin/bash -e

versions=('3.12' '3.13')
compat=('manylinux_2_17' 'manylinux_2_28' 'manylinux_2_34')
targets=(
    'x86_64-unknown-linux-gnu'
)

for target in "${targets[@]}"; do
    for version in "${versions[@]}"; do
        (
            venv_name="/tmp/venv${version}"
            rm -rf "$venv_name"
            virtualenv -p "$(hatch python find "${version}")" "$venv_name"
            "$venv_name/bin/pip" install maturin[patchelf]

            for build in "${compat[@]}"; do
                echo "${version} - ${build};"
                "$venv_name/bin/maturin" build \
                    --release \
                    --target "$target" \
                    --interpreter "$venv_name/bin/python" \
                    --compatibility "$build" \
                    --zig
            done

            "$venv_name/bin/maturin" build \
                --target "$target" \
                --interpreter "$venv_name/bin/python" \
                --release \
                --sdist
        ) &
    done
done

wait
