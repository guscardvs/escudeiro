# Accept Python version as build argument (default: 3.10)
ARG PYVER=3.12

FROM python:${PYVER}-alpine
ARG PYVER
ENV PYVER=${PYVER}

# Install build dependencies
RUN apk update && apk add --no-cache \
    py3-pip \
    py3-virtualenv \
    curl \
    build-base \
    musl-dev \
    git \
    bash \
    zig

RUN curl https://sh.rustup.rs -sSf | sh -s -- --default-toolchain nightly -y

ENV PATH="/root/.cargo/bin:${PATH}"

RUN rustup target add x86_64-unknown-linux-musl

ENV VENV_PATH=/tmp/venv
# Create virtualenv
RUN virtualenv ${VENV_PATH} && \
    # Upgrade pip
    ${VENV_PATH}/bin/pip install --upgrade pip maturin[patchelf]

ENV PATH="${VENV_PATH}/bin:${PATH}"

ENV TARGET_DIR=/musllinux/target

RUN mkdir -p $TARGET_DIR

WORKDIR /escudeiro
COPY . .


CMD ["sh", "-c", "set -e; \
    python -m venv $VENV_PATH; \
    pip install maturin[patchelf]; \
    echo \"Python version: $PYVER\"; \
    maturin build \
        --release \
        --target x86_64-unknown-linux-musl \
        --interpreter python${PYVER} \
        --compatibility musllinux_1_1 \
        --zig; \
    cp -r target/wheels/* $TARGET_DIR/"]
