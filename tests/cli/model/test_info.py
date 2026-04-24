import pytest
from click.testing import CliRunner
from atomforge._host.cli.model.info import info_command

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def successful_invocation(runner):
    result = runner.invoke(info_command, ["ase-lj"])
    return result

def test_success_exit_code(successful_invocation):
    assert successful_invocation.exit_code == 0

def test_success_output_has_kind(successful_invocation):
    assert "Kind" in successful_invocation.output

def test_invalid_model(runner):
    result = runner.invoke(info_command, ["snack"])
    assert result.exit_code == 0
    assert "not found in registry" in result.output