set shell := ["/bin/zsh", "-cu"]

test:
    just test-host

test-host:
    UV_CACHE_DIR=/tmp/uv-cache uv run pytest

test-cov-host:
    UV_CACHE_DIR=/tmp/uv-cache uv run pytest --cov-report term --cov-report xml:.coverage-host.xml --cov src/atomforge

test-cov:
    just test-cov-host

test-cov-sandbox:
    UV_CACHE_DIR=/tmp/uv-cache uv run pytest --cov-report term --cov-report html:.coverage-html --cov src/atomforge

test-core:
    cd packages/atomforge-core && UV_CACHE_DIR=/tmp/uv-cache uv run pytest

test-cov-core:
    cd packages/atomforge-core && UV_CACHE_DIR=/tmp/uv-cache uv run pytest --cov-report term --cov-report xml:.coverage-core.xml --cov src/atomforge_core

test-runtime:
    cd packages/atomforge-runtime && UV_CACHE_DIR=/tmp/uv-cache uv run pytest

test-cov-runtime:
    cd packages/atomforge-runtime && UV_CACHE_DIR=/tmp/uv-cache uv run pytest --cov-report term --cov-report xml:.coverage-runtime.xml --cov src/atomforge_runtime

test-builtins:
    cd packages/atomforge-builtins && UV_CACHE_DIR=/tmp/uv-cache uv run pytest

test-cov-builtins:
    cd packages/atomforge-builtins && UV_CACHE_DIR=/tmp/uv-cache uv run pytest --cov-report term --cov-report xml:.coverage-builtins.xml --cov src/atomforge_builtins

test-all:
    just test-core
    just test-runtime
    just test-builtins
    just test-host

test-cov-all:
    just test-cov-core
    just test-cov-runtime
    just test-cov-builtins
    just test-cov-host

ruff-check:
    uv run ruff check .

ruff-fmt:
    uv run ruff format .
