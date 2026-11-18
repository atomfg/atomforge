"""Export the model plugin template as a standalone project.

    python scripts/template/export.py <out-dir> --rev <atomforge-commit> \
        [--repo-url https://github.com/atomfg/atomforge]

The files are taken from <atomforge-commit> itself (git archive), not from the
working tree, so the exported template and the atomforge it depends on always come
from the same commit. The template's [tool.uv.sources], which point at the packages
in this repository, are replaced by git sources pinned to that commit, and uv.lock
is regenerated. The result is what is mirrored to
atomfg/atomforge-model-plugin-template.
"""

import argparse
import io
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = "templates/model-plugin"
DEFAULT_REPO_URL = "https://github.com/atomfg/atomforge"

# The template's pyproject.toml ends with a comment starting with this line,
# followed by [tool.uv.sources]. Everything from it to the end is replaced.
SOURCES_MARKER = "# Where atomforge comes from."

INDEX_ENV_PREFIXES = ("UV_INDEX", "UV_DEFAULT_INDEX", "UV_EXTRA_INDEX_URL")

# Package name -> subdirectory in the atomforge repository (None: the root).
ATOMFORGE_PACKAGES = {
    "atomforge": None,
    "atomforge_core": "packages/atomforge-core",
    "atomforge_runtime": "packages/atomforge-runtime",
    "atomforge_builtins": "packages/atomforge-builtins",
    "atomforge_testing": "packages/atomforge-testing",
}


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], check=True, capture_output=True
    ).stdout


def resolve_rev(rev: str) -> str:
    """The full commit id; refuses anything that is not a commit in this repo."""
    full = git("rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", full):
        raise SystemExit(f"Not a commit: {rev}")
    return full


def extract_template(rev: str, out_dir: Path) -> None:
    archive = git("archive", "--format=tar", f"{rev}:{TEMPLATE_DIR}")
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(out_dir, filter="data")


def git_sources(repo_url: str, rev: str) -> str:
    lines = [
        SOURCES_MARKER,
        f"# Pinned to atomforge commit {rev[:12]}, which this template was exported",
        "# from. Move all of them together to a newer commit to update atomforge.",
        "[tool.uv.sources]",
    ]
    for name, subdirectory in ATOMFORGE_PACKAGES.items():
        fields = [f'git = "{repo_url}"', f'rev = "{rev}"']
        if subdirectory is not None:
            fields.append(f'subdirectory = "{subdirectory}"')
        lines.append(f"{name} = {{ {', '.join(fields)} }}")
    return "\n".join(lines) + "\n"


def rewrite_sources(pyproject: Path, repo_url: str, rev: str) -> None:
    text = pyproject.read_text()
    if text.count(SOURCES_MARKER) != 1:
        raise SystemExit(
            f"Expected the line {SOURCES_MARKER!r} exactly once in {pyproject}"
        )
    head = text[: text.index(SOURCES_MARKER)]
    pyproject.write_text(head + git_sources(repo_url, rev))


def lock(project: Path) -> None:
    # The archived lockfile resolves the monorepo's path sources; never ship it.
    (project / "uv.lock").unlink(missing_ok=True)
    # Resolve against uv's defaults: the exported lockfile must not depend on index
    # settings of whoever runs the export (CI sets UV_INDEX for torch, for example).
    env = {
        k: v
        for k, v in os.environ.items()
        if k != "VIRTUAL_ENV" and not k.startswith(INDEX_ENV_PREFIXES)
    }
    result = subprocess.run(["uv", "lock", "--quiet"], cwd=project, env=env)
    if result.returncode != 0:
        raise SystemExit(f"uv lock failed in {project}")


def export(out_dir: Path, rev: str, repo_url: str) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory is not empty: {out_dir}")
    if '"' in repo_url or "\\" in repo_url:
        raise SystemExit(f"Unsupported repository URL: {repo_url}")

    rev = resolve_rev(rev)
    out_dir.mkdir(parents=True, exist_ok=True)
    extract_template(rev, out_dir)
    rewrite_sources(out_dir / "pyproject.toml", repo_url, rev)
    lock(out_dir)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--rev", required=True, help="atomforge commit to pin to")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    args = parser.parse_args(argv)
    export(args.out_dir, args.rev, args.repo_url)


if __name__ == "__main__":
    main(sys.argv[1:])
