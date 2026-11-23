"""Acceptance tests for "Containers, design" in the engineering log:
`AtomforgeSettings` reads the environment variables its fields document."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from atomforge.settings.settings import AtomforgeSettings

# (environment variable, value, field, expected field value)
FROM_ENVIRONMENT = [
    (
        "ATOMFORGE_ENV_SEARCH_PATHS",
        os.pathsep.join(["/preloaded/envs", "/more/envs"]),
        "env_search_paths",
        (Path("/preloaded/envs"), Path("/more/envs")),
    ),
    (
        "ATOMFORGE_ENV_INSTALL_PATH",
        "/cache/atomforge/envs",
        "env_install_path",
        Path("/cache/atomforge/envs"),
    ),
    ("ATOMFORGE_ENV_PROVIDER_KIND", "uv", "env_provider_kind", "uv"),
    ("ATOMFORGE_WORKER_INIT_TIMEOUT_S", "12.5", "worker_init_timeout_s", 12.5),
    ("ATOMFORGE_WORKER_TASK_TIMEOUT_S", "60", "worker_task_timeout_s", 60.0),
    (
        "ATOMFORGE_WORKER_SHUTDOWN_TIMEOUT_S",
        "3",
        "worker_shutdown_timeout_s",
        3.0,
    ),
]


def documented_variables() -> dict[str, str]:
    """Field name -> the environment variable its metadata documents."""
    return {
        name: field.json_schema_extra["env_var"]
        for name, field in AtomforgeSettings.model_fields.items()
        if field.json_schema_extra and "env_var" in field.json_schema_extra
    }


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for variable in documented_variables().values():
        monkeypatch.delenv(variable, raising=False)


def test_every_documented_variable_is_tested():
    tested = {(variable, field) for variable, _, field, _ in FROM_ENVIRONMENT}
    documented = {
        (variable, field) for field, variable in documented_variables().items()
    }
    assert tested == documented


@pytest.mark.parametrize(("variable", "value", "field", "expected"), FROM_ENVIRONMENT)
def test_variable_sets_field(monkeypatch, variable, value, field, expected):
    monkeypatch.setenv(variable, value)

    assert getattr(AtomforgeSettings(), field) == expected


@pytest.mark.parametrize(("variable", "value", "field", "expected"), FROM_ENVIRONMENT)
def test_unset_variable_keeps_default(variable, value, field, expected):
    default = AtomforgeSettings.model_fields[field].get_default(
        call_default_factory=True
    )

    assert getattr(AtomforgeSettings(), field) == default


def test_explicit_argument_beats_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("ATOMFORGE_ENV_INSTALL_PATH", "/from/environment")
    monkeypatch.setenv("ATOMFORGE_WORKER_TASK_TIMEOUT_S", "60")

    settings = AtomforgeSettings(env_install_path=tmp_path, worker_task_timeout_s=5)

    assert settings.env_install_path == tmp_path
    assert settings.worker_task_timeout_s == 5.0


@pytest.mark.parametrize(
    "variable", ["ATOMFORGE_WORKER_INIT_TIMEOUT_S", "ATOMFORGE_WORKER_TASK_TIMEOUT_S"]
)
@pytest.mark.parametrize("value", ["none", "None", "NONE"])
def test_none_disables_an_optional_timeout(monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)
    field = {v: f for f, v in documented_variables().items()}[variable]

    assert getattr(AtomforgeSettings(), field) is None


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("ATOMFORGE_WORKER_TASK_TIMEOUT_S", "-1"),
        ("ATOMFORGE_WORKER_TASK_TIMEOUT_S", "soon"),
        ("ATOMFORGE_WORKER_SHUTDOWN_TIMEOUT_S", "none"),
        ("ATOMFORGE_ENV_PROVIDER_KIND", "conda"),
    ],
)
def test_invalid_variable_raises(monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValidationError, match=variable):
        AtomforgeSettings()


def test_backend_without_settings_reads_the_environment(monkeypatch, tmp_path):
    from atomforge.backend.subprocess.backend import SubprocessBackend

    install = tmp_path / "install"
    preloaded = tmp_path / "preloaded"
    preloaded.mkdir()
    monkeypatch.setenv("ATOMFORGE_ENV_INSTALL_PATH", str(install))
    monkeypatch.setenv("ATOMFORGE_ENV_SEARCH_PATHS", str(preloaded))

    backend = SubprocessBackend()
    try:
        provider = backend._environment_provider
        assert provider.install_path == install
        assert preloaded in provider.search_paths
    finally:
        backend.shutdown()
