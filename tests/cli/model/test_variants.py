"""Acceptance tests for "Variants, settings and local weights in the spec,
design" in the engineering log: `atomforge model variants <kind>`, and a
variants count in `atomforge model list`."""

import pytest
from click.testing import CliRunner

from atomforge.cli.model.list import list_command
from atomforge.cli.model.variants import variants_command
from atomforge_runtime.registry.model.model_registry import ModelRegistry

from variant_specs import ORB_LIKE_NAMES, registrations


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_registry(monkeypatch):
    found = registrations()

    def load_entry_points(self):
        for registration in found:
            self._register(registration, registration.kind)

    monkeypatch.setattr(ModelRegistry, "_load_entry_points", load_entry_points)


def test_variants_lists_every_variant(runner, fake_registry):
    result = runner.invoke(variants_command, ["orb-like"])

    assert result.exit_code == 0, result.output
    for name in ORB_LIKE_NAMES:
        assert f"orb-like/{name}" in result.output


def test_variants_of_a_kind_without_variant_fields(runner):
    result = runner.invoke(variants_command, ["ase-lj"])

    assert result.exit_code == 0, result.output
    assert "ase-lj/default" in result.output


def test_variants_of_an_unknown_kind(runner):
    result = runner.invoke(variants_command, ["snack"])

    assert "not found in registry" in result.output


def test_variants_command_is_registered_under_model(runner):
    from atomforge.cli.model import model_cli

    assert "variants" in model_cli.commands


def test_list_has_a_variants_column(runner, fake_registry):
    result = runner.invoke(list_command, ["-c", "v"])

    assert result.exit_code == 0, result.output
    assert "Variants" in result.output
    orb_like_row = next(
        line for line in result.output.splitlines() if "orb-like" in line
    )
    assert "10" in orb_like_row


def test_variants_show_declarations_that_differ_between_them(runner, fake_registry):
    result = runner.invoke(variants_command, ["family-like"])

    assert result.exit_code == 0, result.output
    assert "Precision" in result.output
    small = next(line for line in result.output.splitlines() if "/small" in line)
    large = next(line for line in result.output.splitlines() if "/large" in line)
    assert "f64" in small and "f32" not in small
    assert "f32" in large and "f64" not in large


def test_variants_hide_declarations_that_are_the_same(runner, fake_registry):
    result = runner.invoke(variants_command, ["orb-like"])

    assert "Precision" not in result.output
    assert "Properties" not in result.output


def test_list_shows_the_union_over_variants(runner, fake_registry):
    from atomforge_runtime.registry.model.model_registry import ModelRegistry

    capabilities = (
        ModelRegistry.default().get("family-like").load_resource_capabilities()
    )

    assert capabilities.precision == ["f32", "f64"]
