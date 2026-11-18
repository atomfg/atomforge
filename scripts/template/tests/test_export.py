"""Acceptance tests for exporting the model plugin template to a standalone project.

The export is what gets mirrored to atomfg/atomforge-model-plugin-template. These
tests export the template against this repository's HEAD commit, through a
git+file:// URL, so they test committed code: commit before running them locally.

    uv run pytest scripts/template/tests
    ATOMFORGE_RUN_RUNTIME_TESTS=1 uv run pytest scripts/template/tests   # + runtime
"""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "template" / "export.py"

ATOMFORGE_PACKAGES = {
    "atomforge": None,
    "atomforge-core": "packages/atomforge-core",
    "atomforge-runtime": "packages/atomforge-runtime",
    "atomforge-builtins": "packages/atomforge-builtins",
    "atomforge-testing": "packages/atomforge-testing",
}


def normalize(name: str) -> str:
    return name.replace("_", "-").lower()


def clean_env(**overrides) -> dict[str, str]:
    """The environment for commands in the exported project, outside this repo's venv."""
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env.update(overrides)
    return env


def run(cmd, cwd, env=None):
    result = subprocess.run(
        cmd, cwd=cwd, env=env or clean_env(), capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"{' '.join(map(str, cmd))} failed:\n{result.stdout}\n{result.stderr}"
    )
    return result


@pytest.fixture(scope="module")
def head_rev() -> str:
    return run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT).stdout.strip()


@pytest.fixture(scope="module")
def repo_url() -> str:
    return REPO_ROOT.as_uri()


@pytest.fixture(scope="module")
def exported(tmp_path_factory, head_rev, repo_url) -> Path:
    out = tmp_path_factory.mktemp("export") / "atomforge-model-plugin-template"
    run(
        [
            sys.executable,
            EXPORT_SCRIPT,
            out,
            "--rev",
            head_rev,
            "--repo-url",
            repo_url,
        ],
        cwd=REPO_ROOT,
    )
    return out


def sources(project: Path) -> dict:
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())
    raw = pyproject.get("tool", {}).get("uv", {}).get("sources", {})
    return {normalize(name): source for name, source in raw.items()}


def test_exported_project_has_no_path_sources(exported):
    for name, source in sources(exported).items():
        assert "path" not in source, f"{name} still has a path source: {source}"


def test_atomforge_sources_are_pinned_to_the_commit(exported, head_rev, repo_url):
    exported_sources = sources(exported)

    assert set(ATOMFORGE_PACKAGES) <= set(exported_sources)
    for name, subdirectory in ATOMFORGE_PACKAGES.items():
        source = exported_sources[name]
        assert source.get("git") == repo_url, name
        assert source.get("rev") == head_rev, name
        assert source.get("subdirectory") == subdirectory, name
        assert "tag" not in source and "branch" not in source, name


def test_exported_lockfile_is_up_to_date(exported):
    run(["uv", "lock", "--locked"], cwd=exported)


@pytest.mark.skipif(
    os.environ.get("ATOMFORGE_RUN_RUNTIME_TESTS") != "1",
    reason="Set ATOMFORGE_RUN_RUNTIME_TESTS=1 to run the exported plugin's tests",
)
def test_exported_project_tests_pass(exported, tmp_path):
    # A fresh ~/.atomforge, so worker environments are built from the export's
    # git sources rather than reused. Keep uv's cache to avoid re-downloading.
    uv_cache = run(["uv", "cache", "dir"], cwd=exported).stdout.strip()
    env = clean_env(HOME=str(tmp_path), UV_CACHE_DIR=uv_cache)

    run(["uv", "sync", "--locked"], cwd=exported, env=env)
    run(
        ["uv", "run", "--no-sync", "pytest", "-m", "atomforge_environment"],
        cwd=exported,
        env=env,
    )
    run(
        ["uv", "run", "--no-sync", "pytest"],
        cwd=exported,
        env={**env, "ATOMFORGE_RUN_RUNTIME_TESTS": "1"},
    )
