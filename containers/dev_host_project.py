"""Write a host project for building containers/Dockerfile from the atomforge
working tree, so that the image contains the code as it is now (committed or
not), together with the model plugin template.

    python containers/dev_host_project.py <directory>

The directory gets a copy of the working tree (tracked and untracked files
that git does not ignore) under atomforge/, a pyproject.toml and a uv.lock.
An existing uv.lock is kept and updated, so repeated builds resolve the same
versions. Used by `just build-image-dev` and the image test."""

import shutil
import subprocess
import sys
from pathlib import Path

ATOMFORGE = Path(__file__).resolve().parents[1]

PYPROJECT = """\
[project]
name = "atomforge-dev-image"
version = "0"
requires-python = ">=3.12"
dependencies = [
    "atomforge",
    "atomforge-core",
    "atomforge-runtime",
    "atomforge-builtins",
    "atomforge-template",
]

[tool.uv]
package = false

[tool.uv.sources]
atomforge = { path = "atomforge", editable = true }
atomforge-core = { path = "atomforge/packages/atomforge-core", editable = true }
atomforge-runtime = { path = "atomforge/packages/atomforge-runtime", editable = true }
atomforge-builtins = { path = "atomforge/packages/atomforge-builtins", editable = true }
atomforge-template = { path = "atomforge/templates/model-plugin", editable = true }
"""


def working_tree_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ATOMFORGE,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [
        name for name in listed.split("\0") if name and (ATOMFORGE / name).is_file()
    ]


def write_host_project(directory: Path) -> Path:
    directory = Path(directory).resolve()
    if directory == ATOMFORGE or directory in ATOMFORGE.parents:
        raise ValueError(f"refusing to write a host project into {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    copy = directory / "atomforge"
    if copy.exists():
        shutil.rmtree(copy)
    for name in working_tree_files():
        target = copy / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ATOMFORGE / name, target)
    (directory / "pyproject.toml").write_text(PYPROJECT)
    subprocess.run(["uv", "lock", "--quiet"], cwd=directory, check=True)
    return directory


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(write_host_project(Path(sys.argv[1])))
