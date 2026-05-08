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
    #!/usr/bin/env bash
    set -euo pipefail
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT
    venv="$tmpdir/venv"
    wheels=(
        packages/atomforge-core/dist/*.whl
        packages/atomforge-runtime/dist/*.whl
        packages/atomforge-builtins/dist/*.whl
        packages/atomforge-testing/dist/*.whl
        dist/*.whl
    )
    for wheel in "${wheels[@]}"; do
        if [[ ! -f "$wheel" ]]; then
            echo "Missing built wheel: $wheel" >&2
            exit 1
        fi
    done
    uv venv --python 3.13 "$venv"
    uv pip install --python "$venv/bin/python" "${wheels[@]}"
    "$venv/bin/atomforge" --help >/dev/null
    "$venv/bin/python" - <<'PY'
    import importlib.metadata as metadata

    import atomforge
    import atomforge_builtins
    import atomforge_core
    import atomforge_runtime
    import atomforge_testing

    task_names = {entry_point.name for entry_point in metadata.entry_points(group="atomforge.task")}
    model_names = {entry_point.name for entry_point in metadata.entry_points(group="atomforge.model")}
    missing_tasks = {"single_point", "bfgs", "optimize", "analyze_symmetry", "atomic_descriptor"} - task_names
    missing_models = {"lennard_jones", "no_dep"} - model_names
    if missing_tasks or missing_models:
        raise SystemExit(
            f"Missing entry points: tasks={sorted(missing_tasks)}, models={sorted(missing_models)}"
        )
    PY

select-release-files:
    #!/usr/bin/env bash
    set -euo pipefail
    python - <<'PY'
    from __future__ import annotations

    import json
    import re
    import sys
    import tomllib
    import urllib.error
    import urllib.request
    from pathlib import Path

    PACKAGE_DIRS = [
        Path("packages/atomforge-core"),
        Path("packages/atomforge-runtime"),
        Path("packages/atomforge-builtins"),
        Path("packages/atomforge-testing"),
        Path("."),
    ]

    def normalize_name(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    def published_versions(package_name: str) -> set[str]:
        normalized = normalize_name(package_name)
        url = f"https://pypi.org/pypi/{normalized}/json"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return set()
            raise SystemExit(f"Failed to query {url}: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise SystemExit(f"Failed to query {url}: {exc.reason}") from exc
        return set(payload.get("releases", {}))

    def read_project(package_dir: Path) -> tuple[str, str]:
        with (package_dir / "pyproject.toml").open("rb") as file:
            project = tomllib.load(file)["project"]
        return project["name"], project["version"]

    def artifact_prefixes(package_name: str, version: str) -> set[str]:
        normalized = normalize_name(package_name)
        return {
            f"{normalized}-{version}",
            f"{normalized.replace('-', '_')}-{version}",
        }

    def find_artifacts(package_dir: Path, package_name: str, version: str) -> list[Path]:
        dist_dir = package_dir / "dist"
        prefixes = artifact_prefixes(package_name, version)
        artifacts = [
            artifact
            for artifact in dist_dir.glob("*")
            if artifact.is_file()
            and artifact.name.endswith((".whl", ".tar.gz"))
            and any(artifact.name.startswith(prefix) for prefix in prefixes)
        ]
        return sorted(artifacts)

    selected: list[Path] = []
    for package_dir in PACKAGE_DIRS:
        package_name, version = read_project(package_dir)
        if version in published_versions(package_name):
            print(f"{package_name} {version} already exists on PyPI; skipping.", file=sys.stderr)
            continue
        artifacts = find_artifacts(package_dir, package_name, version)
        if not artifacts:
            raise SystemExit(
                f"{package_name} {version} is not on PyPI, but no matching artifacts were found."
            )
        selected.extend(artifacts)

    for artifact in selected:
        print(artifact.as_posix())
    PY

ruff-check:
    uv run ruff check .

ruff-fmt:
    uv run ruff format .
