"""An install path that cannot be written, as in a container whose /cache is
not bound to a writable directory. Found when running the image on the
cluster (see "Containers, design" in the engineering log): `atomforge env
list` failed with a traceback, because the provider created the install path
when it was constructed.

Reading (listing, using preloaded environments) must work without a writable
install path. Building must fail with an error that names the install path
and how to set it, before uv runs."""

import os
import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from atomforge.cli.main import main
from atomforge.env.base.provider import InstallPathNotWritable
from atomforge.env.uv.uv import UVEnvironmentProvider
from atomforge_core.env.env import EnvironmentSpec

from fake_uv import install_fake_uv

pytestmark = pytest.mark.skipif(
    os.geteuid() == 0, reason="root can write to read-only directories"
)

SPEC = EnvironmentSpec(name="lj-single_point", requirements=["ase"])
OTHER_SPEC = EnvironmentSpec(name="lj-analyze_symmetry", requirements=["pymatgen"])


@pytest.fixture
def fake_uv(monkeypatch):
    return install_fake_uv(monkeypatch)


@pytest.fixture
def preloaded(tmp_path, fake_uv) -> Path:
    root = tmp_path / "preloaded"
    UVEnvironmentProvider(search_path=(), install_path=root).ensure_environment(SPEC)
    fake_uv.calls.clear()
    return root


@pytest.fixture(params=["missing", "existing"])
def unwritable_install(request, tmp_path) -> Path:
    """An install path that does not exist under a read-only directory, or
    one that exists and is read-only."""
    parent = tmp_path / "read-only"
    parent.mkdir()
    path = parent / "envs"
    if request.param == "existing":
        path.mkdir()
        locked = [path, parent]
    else:
        locked = [parent]
    for directory in locked:
        directory.chmod(stat.S_IRUSR | stat.S_IXUSR)
    yield path
    for directory in locked:
        directory.chmod(stat.S_IRWXU)


def invoke(*args: str):
    return CliRunner().invoke(main, list(args), env={"COLUMNS": "1000"})


def test_provider_is_constructed_without_creating_the_install_path(tmp_path):
    install = tmp_path / "not-yet" / "envs"

    UVEnvironmentProvider(search_path=(), install_path=install)

    assert not install.exists()


def test_preloaded_environment_is_used_with_unwritable_install_path(
    preloaded, unwritable_install, fake_uv
):
    provider = UVEnvironmentProvider(
        search_path=(preloaded,), install_path=unwritable_install
    )

    handle = provider.ensure_environment(SPEC)

    assert handle.path.is_relative_to(preloaded)
    assert fake_uv.calls == []


def test_building_with_unwritable_install_path_names_the_path(
    preloaded, unwritable_install, fake_uv
):
    provider = UVEnvironmentProvider(
        search_path=(preloaded,), install_path=unwritable_install
    )

    with pytest.raises(InstallPathNotWritable) as error:
        provider.ensure_environment(OTHER_SPEC)

    assert str(unwritable_install) in str(error.value)
    assert "ATOMFORGE_ENV_INSTALL_PATH" in str(error.value)
    assert fake_uv.syncs() == []


def test_env_list_works_with_unwritable_install_path(
    preloaded, unwritable_install, monkeypatch, fake_uv
):
    monkeypatch.setenv("ATOMFORGE_ENV_SEARCH_PATHS", str(preloaded))
    monkeypatch.setenv("ATOMFORGE_ENV_INSTALL_PATH", str(unwritable_install))

    result = invoke("env", "list")

    assert result.exit_code == 0, result.output
    [key] = [p.name for p in (preloaded / "uv").iterdir()]
    assert key in result.output


def test_env_preload_into_unwritable_install_path_fails_cleanly(
    tmp_path, unwritable_install, monkeypatch, fake_uv
):
    monkeypatch.setenv("ATOMFORGE_ENV_INSTALL_PATH", str(unwritable_install))
    # Not the default search paths, which may already hold the environment.
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("ATOMFORGE_ENV_SEARCH_PATHS", str(empty))

    result = invoke("env", "preload", "ase-lj")

    assert result.exit_code != 0
    # A ClickException, not a traceback.
    assert isinstance(result.exception, SystemExit)
    assert str(unwritable_install) in result.output
    assert fake_uv.syncs() == []
