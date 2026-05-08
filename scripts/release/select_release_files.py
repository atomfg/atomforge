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
    # Path("packages/atomforge-runtime"),
    # Path("packages/atomforge-builtins"),
    # Path("packages/atomforge-testing"),
    # Path("."),
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
    return sorted(
        artifact
        for artifact in dist_dir.glob("*")
        if artifact.is_file()
        and artifact.name.endswith((".whl", ".tar.gz"))
        and any(artifact.name.startswith(prefix) for prefix in prefixes)
    )


def main() -> int:
    selected: list[Path] = []
    for package_dir in PACKAGE_DIRS:
        package_name, version = read_project(package_dir)
        if version in published_versions(package_name):
            print(
                f"{package_name} {version} already exists on PyPI; skipping.",
                file=sys.stderr,
            )
            continue
        artifacts = find_artifacts(package_dir, package_name, version)
        if not artifacts:
            raise SystemExit(
                f"{package_name} {version} is not on PyPI, "
                "but no matching artifacts were found."
            )
        selected.extend(artifacts)

    for artifact in selected:
        print(artifact.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
