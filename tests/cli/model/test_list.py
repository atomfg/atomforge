from dataclasses import replace

import pytest
from click.testing import CliRunner
from atomforge.cli.model.list import list_command
from atomforge_core.registry.symbol_path import SymbolPath
from atomforge_runtime.registry.model.model_registry import ModelRegistry

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def successful_invocation(runner):
    result = runner.invoke(list_command)
    return result

@pytest.fixture
def failed_invocation(runner):
    result = runner.invoke(list_command, ["--invalid-option"])
    return result

@pytest.fixture
def column_select_invocation(runner):
    result = runner.invoke(list_command, ["-c", "sad"])
    return result

@pytest.fixture
def strict_invocation(runner):
    result = runner.invoke(list_command, ["--strict"])
    return result

@pytest.fixture(params=["empirical", "mlip"])
def family_type(request):
    return request.param

@pytest.fixture
def family_filter_invocation(runner, family_type):
    result = runner.invoke(list_command, ["-f", family_type])
    return result

def test_success_exit_code(successful_invocation):
    assert successful_invocation.exit_code == 0

def test_success_output_has_kind(successful_invocation):
    assert "Kind" in successful_invocation.output

def test_failed_exit_code(failed_invocation):
    assert failed_invocation.exit_code != 0

def test_failed_output_has_error_message(failed_invocation):
    assert "Error" in failed_invocation.output

def test_column_select_exit_code(column_select_invocation):
    assert column_select_invocation.exit_code == 0

def test_column_select_output_has_selected_column(column_select_invocation):
    assert "Supported Properties" in column_select_invocation.output
    assert "Dependencies" in column_select_invocation.output
    assert "Accelerator" in column_select_invocation.output

def test_column_select_output_does_not_have_unselected_columns(column_select_invocation):
    assert "Plugin Source" not in column_select_invocation.output
    assert "Family" not in column_select_invocation.output

def test_strict_exit_code(strict_invocation):
    assert strict_invocation.exit_code == 0

def test_strict_output_has_status_column(strict_invocation):
    assert "Strict" in strict_invocation.output

def test_strict_output_marks_valid_models(strict_invocation):
    assert "PASS" in strict_invocation.output

def test_strict_output_has_kind(strict_invocation):
    assert "Kind" in strict_invocation.output

def test_strict_shows_failing_models(runner, monkeypatch):
    registry = ModelRegistry.default()
    broken = replace(
        registry.get("ase-lj"),
        kind="broken-ase-lj",
        metadata_path=SymbolPath("atomforge.registry.model.manifest:ModelManifest"),
    )
    registry._register(broken, broken.kind)

    monkeypatch.setattr(
        "atomforge_runtime.registry.model.model_registry.ModelRegistry.default",
        lambda: registry,
    )

    result = runner.invoke(list_command, ["--strict"])

    assert result.exit_code == 0
    assert "FAIL" in result.output
    assert "broken-ase-lj" in result.output

def test_family_filter_exit_code(family_filter_invocation):
    assert family_filter_invocation.exit_code == 0

def test_family_filter(family_filter_invocation, family_type):
    if family_type == "empirical":
        assert "ase-lj" in family_filter_invocation.output
    else:
        assert "ase-lj" not in family_filter_invocation.output
