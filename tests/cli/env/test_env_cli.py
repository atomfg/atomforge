"""Acceptance tests for "Containers, design" in the engineering log:
`atomforge env preload` and `atomforge env list`.

A worker environment is the model's environment plus the task's, so preload
takes the tasks to build for (`--task`, repeatable, default `single_point`).
`uv` is replaced by a fake; the image test builds real environments."""

import logging
from pathlib import Path

import pytest
from click.testing import CliRunner

from atomforge.cli.main import main
from atomforge.env.uv.uv import UVEnvironmentProvider
from atomforge_builtins.model.ase_lj.spec import LennardJones
from atomforge_builtins.task.analyze_symmetry.spec import AnalyzeSymmetry
from atomforge_builtins.task.bfgs.spec import BFGS
from atomforge_builtins.task.single_point.spec import SinglePoint
from atomforge_runtime.registry.model.model_registry import ModelRegistry
from atomforge_runtime.registry.task.task_registry import TaskRegistry

from fake_uv import install_fake_uv


@pytest.fixture
def fake_uv(monkeypatch):
    return install_fake_uv(monkeypatch)


@pytest.fixture
def install(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "install"
    monkeypatch.setenv("ATOMFORGE_ENV_INSTALL_PATH", str(path))
    monkeypatch.delenv("ATOMFORGE_ENV_SEARCH_PATHS", raising=False)
    return path


def invoke(*args: str):
    # Wide enough that a table never truncates a temporary path.
    return CliRunner().invoke(main, list(args), env={"COLUMNS": "1000"})


def expected_key(install: Path, model, task) -> str:
    """The key of the environment a backend would use to run `task` with
    `model`."""
    model_env = (
        ModelRegistry.default().get(model.kind).load_environment_factory()(model)
    )
    task_env = TaskRegistry.default().get(task.kind).load_environment_factory()(task)
    provider = UVEnvironmentProvider(search_path=(), install_path=install)
    return provider.environment_key(model_env + task_env)


def preloaded_keys(root: Path) -> set[str]:
    return {path.name for path in (root / "uv").iterdir() if path.is_dir()}


def test_preload_builds_the_single_point_environment(
    install, fake_uv, example_structure
):
    result = invoke("env", "preload", "ase-lj")

    assert result.exit_code == 0, result.output
    key = expected_key(
        install, LennardJones(), SinglePoint(structure=example_structure)
    )
    assert preloaded_keys(install) == {key}


def test_preloaded_environment_is_found_without_uv(
    tmp_path, install, fake_uv, example_structure
):
    invoke("env", "preload", "ase-lj")
    fake_uv.calls.clear()
    provider = UVEnvironmentProvider(
        search_path=(install,), install_path=tmp_path / "elsewhere"
    )
    model_env = (
        ModelRegistry.default().get("ase-lj").load_environment_factory()(LennardJones())
    )
    task = SinglePoint(structure=example_structure)
    task_env = TaskRegistry.default().get(task.kind).load_environment_factory()(task)

    handle = provider.ensure_environment(model_env + task_env)

    assert handle.path.is_relative_to(install)
    assert fake_uv.calls == []


def test_preload_twice_builds_once(install, fake_uv):
    first = invoke("env", "preload", "ase-lj")
    fake_uv.calls.clear()

    second = invoke("env", "preload", "ase-lj")

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert fake_uv.syncs() == []


def test_preload_with_profile(install, fake_uv, example_structure):
    result = invoke("env", "preload", "ase-lj:latest")

    assert result.exit_code == 0, result.output
    key = expected_key(
        install,
        LennardJones(environment_profile="latest"),
        SinglePoint(structure=example_structure),
    )
    assert preloaded_keys(install) == {key}


def test_preload_for_several_tasks_builds_each_environment_once(
    install, fake_uv, example_structure
):
    result = invoke(
        "env",
        "preload",
        "ase-lj",
        "--task",
        "single_point",
        "--task",
        "bfgs",
        "--task",
        "analyze_symmetry",
    )

    assert result.exit_code == 0, result.output
    model = LennardJones()
    keys = {
        expected_key(install, model, task)
        for task in (
            SinglePoint(structure=example_structure),
            BFGS(structure=example_structure),
            AnalyzeSymmetry(structure=example_structure),
        )
    }
    # single_point and bfgs share an environment with ase-lj.
    assert len(keys) == 2
    assert preloaded_keys(install) == keys
    assert len(fake_uv.syncs()) == 2


@pytest.mark.parametrize(
    ("argument", "named"),
    [("no-such-model", "no-such-model"), ("ase-lj:no-such-profile", "no-such-profile")],
)
def test_preload_of_unknown_model_or_profile_fails(install, fake_uv, argument, named):
    result = invoke("env", "preload", argument)

    assert result.exit_code != 0
    assert named in result.output
    assert fake_uv.syncs() == []


def test_preload_of_unknown_task_fails(install, fake_uv):
    result = invoke("env", "preload", "ase-lj", "--task", "no-such-task")

    assert result.exit_code != 0
    assert "no-such-task" in result.output
    assert fake_uv.syncs() == []


def test_list_shows_preloaded_and_installed_environments(
    tmp_path, monkeypatch, fake_uv, example_structure
):
    preloaded = tmp_path / "preloaded"
    install = tmp_path / "install"
    monkeypatch.setenv("ATOMFORGE_ENV_INSTALL_PATH", str(preloaded))
    assert invoke("env", "preload", "ase-lj").exit_code == 0
    monkeypatch.setenv("ATOMFORGE_ENV_INSTALL_PATH", str(install))
    assert invoke("env", "preload", "ase-lj:latest").exit_code == 0
    monkeypatch.setenv("ATOMFORGE_ENV_SEARCH_PATHS", str(preloaded))

    result = invoke("env", "list")

    assert result.exit_code == 0, result.output
    structure = SinglePoint(structure=example_structure)
    rows = {
        "preloaded": (
            expected_key(install, LennardJones(), structure),
            preloaded,
        ),
        "installed": (
            expected_key(
                install, LennardJones(environment_profile="latest"), structure
            ),
            install,
        ),
    }
    lines = result.output.splitlines()
    for where, (key, root) in rows.items():
        [line] = [line for line in lines if key in line]
        assert str(root / "uv" / key) in line
        assert ("read-only" in line) == (where == "preloaded")


def test_preload_does_not_warn_about_building(
    tmp_path, install, monkeypatch, fake_uv, caplog
):
    # Found while implementing: a preload is a deliberate build, so the
    # run-time warning must not fire even when other search paths exist.
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("ATOMFORGE_ENV_SEARCH_PATHS", str(other))

    with caplog.at_level(logging.WARNING, logger="atomforge"):
        result = invoke("env", "preload", "ase-lj")

    assert result.exit_code == 0, result.output
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
