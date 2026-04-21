import pytest
from click.testing import CliRunner
from atomforge.cli.model.list import list_command

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

def test_family_filter_exit_code(family_filter_invocation):
    assert family_filter_invocation.exit_code == 0

def test_family_filter(family_filter_invocation, family_type):
    if family_type == "empirical":
        assert "ase-lj" in family_filter_invocation.output
    else:
        assert "ase-lj" not in family_filter_invocation.output

