#!/bin/bash -e

versions=('3.12' '3.13')
compat=('manylinux_2_17' 'manylinux_2_28' 'manylinux_2_34')
targets=(
    'x86_64-unknown-linux-gnu'
)

for target in "${targets[@]}"; do
    for version in "${versions[@]}"; do
        (
            for build in "${compat[@]}"; do
                echo "${version} - ${build};"
                uv run --python "${version}" maturin build \
                    --release \
                    --target "$target" \
                    --interpreter "$venv_name/bin/python" \
                    --compatibility "$build" \
                    --zig
            done

            uv run --python "${version}" maturin build \
                --target "$target" \
                --interpreter "$venv_name/bin/python" \
                --release \
                --sdist
        ) &
    done
done

wait
