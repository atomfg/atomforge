test:
    just test-host

test-host:
    uv run pytest

test-cov-host:
    uv run pytest --cov-report term --cov-report xml:.coverage-host.xml --cov src/atomforge

test-cov:
    just test-cov-host

test-cov-sandbox:
    uv run pytest --cov-report term --cov-report html:.coverage-html --cov src/atomforge

test-core:
    cd packages/atomforge-core && uv run pytest

test-cov-core:
    cd packages/atomforge-core && uv run pytest --cov-report term --cov-report xml:.coverage-core.xml --cov src/atomforge_core

test-runtime:
    cd packages/atomforge-runtime && uv run pytest

test-cov-runtime:
    cd packages/atomforge-runtime && uv run pytest --cov-report term --cov-report xml:.coverage-runtime.xml --cov src/atomforge_runtime

test-builtins:
    cd packages/atomforge-builtins && uv run pytest

test-cov-builtins:
    cd packages/atomforge-builtins && uv run pytest --cov-report term --cov-report xml:.coverage-builtins.xml --cov src/atomforge_builtins

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


build-host:
    uv build

build-core:
    cd packages/atomforge-core && uv build

build-runtime:
    cd packages/atomforge-runtime && uv build

build-builtins:
    cd packages/atomforge-builtins && uv build

build-testing:
    cd packages/atomforge-testing && uv build

build-all:
    just build-host
    just build-core
    just build-runtime
    just build-builtins
    just build-testing

sync:
    uv sync

clean-release:
    rm -rf packages/atomforge-core/dist
    rm -rf packages/atomforge-runtime/dist
    rm -rf packages/atomforge-builtins/dist
    rm -rf packages/atomforge-testing/dist
    rm -rf dist

build-release:
    just clean-release
    just build-core
    just build-runtime
    just build-builtins
    just build-testing
    just build-host

validate-release-tag TAG="":
    #!/usr/bin/env bash
    set -euo pipefail
    tag_arg='{{TAG}}'
    if [[ "$tag_arg" == TAG=* ]]; then
        tag_arg="${tag_arg#TAG=}"
    fi
    tag="${tag_arg:-${GITHUB_REF_NAME:-${TAG:-}}}"
    if [[ -z "$tag" ]]; then
        echo "No release tag provided. Set GITHUB_REF_NAME or pass TAG=..." >&2
        exit 1
    fi
    if [[ ! "$tag" =~ ^v[0-9]{2}\.[0-9]{2}\.[0-9]{2}([.-][A-Za-z0-9][A-Za-z0-9._-]*)?$ ]]; then
        echo "Invalid release tag: $tag" >&2
        echo "Expected vDD.MM.YY with optional .specifier or -specifier suffix." >&2
        exit 1
    fi
    echo "Release tag is valid: $tag"

smoke-release:
    python scripts/release/smoke_release.py

select-release-files:
    python scripts/release/select_release_files.py

ruff-check:
    uv run ruff check .

ruff-fmt:
    uv run ruff format .
