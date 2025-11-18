versions=('3.12' '3.13' '3.14')
targets=(
    'x86_64-pc-windows-gnu'
    'i686-pc-windows-gnu'
    'x86_64-pc-windows-msvc'
    'i686-pc-windows-msvc'
)

for target in "${targets[@]}"; do
    for version in "${versions[@]}"; do
        (
            echo "Building for Python ${version} on target ${target};"
            uv run --isolated --python "${version}" maturin build \
                --release \
                --target "$target"

            uv run --isolated --python "${version}" maturin build \
                --release \
                --target "$target"
        ) &
    done
done
