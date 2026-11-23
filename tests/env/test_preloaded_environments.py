"""Acceptance tests for "Containers, design" in the engineering log: read-only
search paths, and environments built at run time.

An environment in a search path other than the install path is preloaded: it
is found without running uv and is never modified or removed. Environments in
the install path keep today's `uv sync --check`. `uv` is replaced by a fake
that records its calls, so no environment is really built."""

import logging
import stat
import subprocess
from pathlib import Path

import pytest

from atomforge.env.uv.uv import UVEnvironmentProvider
from atomforge_core.env.env import EnvironmentSpec

from fake_uv import install_fake_uv

SPEC = EnvironmentSpec(name="lj-single_point", requirements=["ase"])


@pytest.fixture
def fake_uv(monkeypatch):
    return install_fake_uv(monkeypatch)


@pytest.fixture
def preloaded(tmp_path, fake_uv) -> Path:
    """A directory holding SPEC's environment, built as an image build
    would: with that directory as the install path."""
    root = tmp_path / "preloaded"
    UVEnvironmentProvider(search_path=(), install_path=root).ensure_environment(SPEC)
    fake_uv.calls.clear()
    return root


def snapshot(root: Path) -> dict[str, tuple[int, int]]:
    return {
        str(path.relative_to(root)): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in sorted(root.rglob("*"))
    }


def make_read_only(root: Path) -> None:
    for path in [root, *root.rglob("*")]:
        mode = path.stat().st_mode
        path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


@pytest.fixture
def restore_permissions(preloaded):
    yield
    for path in [preloaded, *preloaded.rglob("*")]:
        path.chmod(path.stat().st_mode | stat.S_IWUSR)


def test_preloaded_environment_is_found_without_uv(tmp_path, preloaded, fake_uv):
    provider = UVEnvironmentProvider(
        search_path=(preloaded,), install_path=tmp_path / "install"
    )

    handle = provider.ensure_environment(SPEC)

    assert handle.path.parent.parent == preloaded
    assert fake_uv.calls == []


def test_preloaded_environment_is_used_from_a_read_only_directory(
    tmp_path, preloaded, fake_uv, restore_permissions, monkeypatch
):
    make_read_only(preloaded)
    before = snapshot(preloaded)
    provider = UVEnvironmentProvider(
        search_path=(preloaded,), install_path=tmp_path / "install"
    )

    def refuse_removal(handle):
        raise AssertionError(f"removed {handle.path}")

    monkeypatch.setattr(provider, "remove_environment", refuse_removal)

    handle = provider.ensure_environment(SPEC)
    info = provider.inspect_environment(handle)

    assert info.python_executable == handle.path / ".venv" / "bin" / "python"
    assert snapshot(preloaded) == before
    assert fake_uv.calls == []


def test_provenance_of_preloaded_environment_points_into_it(
    tmp_path, preloaded, fake_uv
):
    provider = UVEnvironmentProvider(
        search_path=(preloaded,), install_path=tmp_path / "install"
    )

    handle = provider.ensure_environment(SPEC)
    provenance = provider.build_provenance(SPEC, handle)

    assert Path(provenance.path).is_relative_to(preloaded)
    assert provenance.key == provider.environment_key(SPEC)
    assert provenance.lockfile_hash is not None


def test_environment_without_marker_is_skipped_and_kept(tmp_path, fake_uv):
    # A directory with the right key but not built by a completed preload
    # (an older atomforge, or an interrupted build).
    stale = tmp_path / "stale"
    install = tmp_path / "install"
    key = UVEnvironmentProvider(search_path=(), install_path=install).environment_key(
        SPEC
    )
    python = stale / "uv" / key / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("")
    (stale / "uv" / key / "uv.lock").write_text("lock")
    before = snapshot(stale)
    provider = UVEnvironmentProvider(search_path=(stale,), install_path=install)
    assert stale in provider.search_paths

    handle = provider.ensure_environment(SPEC)

    assert handle.path == tmp_path / "install" / "uv" / key
    assert snapshot(stale) == before
    assert fake_uv.checks() == []


def test_failed_build_leaves_no_preloadable_environment(tmp_path, fake_uv):
    root = tmp_path / "preloaded"
    fake_uv.sync_fails = True
    with pytest.raises((subprocess.CalledProcessError, RuntimeError)):
        UVEnvironmentProvider(search_path=(), install_path=root).ensure_environment(
            SPEC
        )
    fake_uv.sync_fails = False
    fake_uv.calls.clear()

    provider = UVEnvironmentProvider(
        search_path=(root,), install_path=tmp_path / "install"
    )
    handle = provider.ensure_environment(SPEC)

    assert handle.path.is_relative_to(tmp_path / "install")
    assert fake_uv.syncs() == [handle.path]


def test_install_path_environment_is_still_checked_with_uv(tmp_path, fake_uv):
    install = tmp_path / "install"
    provider = UVEnvironmentProvider(search_path=(), install_path=install)
    built = provider.ensure_environment(SPEC)
    fake_uv.calls.clear()

    handle = provider.ensure_environment(SPEC)

    assert handle.path == built.path
    assert fake_uv.checks() == [built.path]
    assert fake_uv.syncs() == []


def test_install_path_environment_failing_its_check_is_rebuilt(tmp_path, fake_uv):
    install = tmp_path / "install"
    provider = UVEnvironmentProvider(search_path=(), install_path=install)
    built = provider.ensure_environment(SPEC)
    fake_uv.calls.clear()
    fake_uv.check_returncode = 1

    handle = provider.ensure_environment(SPEC)

    assert handle.path == built.path
    assert fake_uv.checks() == [built.path]
    assert fake_uv.syncs() == [built.path]


def test_building_an_environment_missing_from_preloaded_paths_warns(
    tmp_path, fake_uv, caplog
):
    preloaded = tmp_path / "preloaded"
    preloaded.mkdir()
    provider = UVEnvironmentProvider(
        search_path=(preloaded,), install_path=tmp_path / "install"
    )

    with caplog.at_level(logging.WARNING, logger="atomforge"):
        handle = provider.ensure_environment(SPEC)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert SPEC.name in message
    assert provider.environment_key(SPEC) in message
    assert str(handle.path) in message


def test_building_an_environment_without_preloaded_paths_does_not_warn(
    tmp_path, fake_uv, caplog
):
    install = tmp_path / "install"
    provider = UVEnvironmentProvider(search_path=(install,), install_path=install)

    with caplog.at_level(logging.WARNING, logger="atomforge"):
        provider.ensure_environment(SPEC)

    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
