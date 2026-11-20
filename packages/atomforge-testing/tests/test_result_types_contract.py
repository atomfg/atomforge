"""Acceptance tests for the result types contract (the "Checking model results
in tests, design" entry in the engineering log).

`ModelResultTypesContract` runs the describe_model_result task for each
declared property on its own and for all declared properties together, and
checks the description of the raw ``ModelResult`` with one assert per test.
Each test here runs the contract in an inner pytest session, against a
backend that runs the real task executor in process with a fake model
executor that is correct or broken in one way.
"""

from pathlib import Path
import re
import sys

import pytest

TESTS_PATH = Path(__file__).resolve().parent

if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))

import testing_fakes  # noqa: E402
from atomforge_core.property import Property  # noqa: E402

PYPROJECT = """\
[project]
name = "fake-plugin"

[project.entry-points.'atomforge.model']
fake = "testing_fakes:fake_manifest"
"""

CASE_MODULE = """\
from pathlib import Path

from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_testing import ModelManifestCase, structures

PYPROJECT = Path(__file__).parent / "pyproject.toml"

MANIFEST = ModelManifest(
    kind="fake-model",
    model_spec="testing_fakes:FakeModel",
    executor_cls="testing_fakes:{executor}",
    supported_properties="testing_fakes:{properties}",
    environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
    metadata="testing_fakes:FakeMetadata",
    resource_capabilities="testing_fakes:FakeResourceCapabilities",
    distribution="fake-plugin",
)

CASE = ModelManifestCase(
    manifest=MANIFEST,
    entry_point_name="fake",
    entry_point_package="fake-plugin",
    pyproject_path=PYPROJECT,
    expected_entry_point_target="testing_fakes:fake_manifest",
    runtime_structure=structures.small_molecule(),
)
"""

CONFTEST = """\
import pytest

from fake_case import CASE
from testing_fakes import TaskRunningBackend


@pytest.fixture(scope="session")
def atomforge_backend():
    return TaskRunningBackend(CASE.manifest)
"""

TESTS = """\
from fake_case import CASE
from atomforge_testing import ModelResultTypesContract


class TestFake(ModelResultTypesContract):
    manifest_case = CASE
"""

CHECKS = (
    "test_requested_properties_are_described",
    "test_energy_is_a_float",
    "test_energy_is_finite",
    "test_forces_have_one_row_per_atom",
    "test_forces_rows_are_three_floats",
    "test_forces_are_finite",
    "test_stress_is_three_rows_of_three_floats",
    "test_stress_is_finite",
    "test_energies_have_one_float_per_atom",
    "test_energies_are_finite",
    "test_magmoms_have_one_float_per_atom",
    "test_magmoms_are_finite",
)

PROPERTY_REQUESTS = ("energy", "forces", "stress", "energies", "magmoms")


def write_project(
    pytester, *, executor="AllPropertiesExecutor", properties="AllSupportedProperties"
):
    pytester.makefile(".toml", pyproject=PYPROJECT)
    pytester.makepyfile(
        fake_case=CASE_MODULE.format(executor=executor, properties=properties)
    )
    pytester.makeconftest(CONFTEST)
    pytester.makepyfile(test_contracts=TESTS)
    pytester.syspathinsert()


OUTCOME = re.compile(r"::(\w+)\[([^\]]*)\] (PASSED|FAILED|SKIPPED|ERROR)")


def run(pytester, *args) -> dict[tuple[str, str], str]:
    """Outcome per (check, request), e.g. ``("test_energy_is_a_float",
    "all")``. The request is the last part of the test id, after the
    environment profile."""
    result = pytester.runpytest_inprocess("-v", *args)
    found = {}
    for line in result.outlines:
        match = OUTCOME.search(line)
        if match:
            request = match.group(2).split("-")[-1]
            found[(match.group(1), request)] = match.group(3)
    return found


@pytest.fixture(autouse=True)
def reset_recorders():
    testing_fakes.InProcessBackend.instances = []


def requests_made():
    return [
        task
        for backend in testing_fakes.InProcessBackend.instances
        for task, _, _ in backend.requests
    ]


# The contract's shape


def test_contract_has_one_test_per_check():
    from atomforge_testing import ModelResultTypesContract

    names = {name for name in dir(ModelResultTypesContract) if name.startswith("test_")}
    assert names == set(CHECKS)


def test_plugin_contract_includes_the_result_types_contract():
    from atomforge_testing import ModelPluginContract, ModelResultTypesContract

    assert issubclass(ModelPluginContract, ModelResultTypesContract)


def test_contract_runs_only_with_the_runtime_option(pytester):
    write_project(pytester)

    found = run(pytester)

    assert set(found.values()) == {"SKIPPED"}


# What it requests


def test_contract_requests_each_declared_property_and_all_together(pytester):
    write_project(pytester)

    run(pytester, "--atomforge-runtime")

    requested = {task.properties for task in requests_made()}
    expected = {frozenset({p}) for p in testing_fakes.ALL_PROPERTIES}
    assert requested == expected | {testing_fakes.ALL_PROPERTIES}


def test_contract_uses_the_describe_task(pytester):
    write_project(pytester)

    run(pytester, "--atomforge-runtime")

    assert {task.kind for task in requests_made()} == {"describe_model_result"}


def test_stress_is_requested_on_a_periodic_structure(pytester):
    write_project(pytester)

    run(pytester, "--atomforge-runtime")

    with_stress = [t for t in requests_made() if Property.STRESS in t.properties]
    assert with_stress and all(any(t.structure.pbc) for t in with_stress)


def test_undeclared_properties_are_not_requested(pytester):
    write_project(pytester, properties="FakeSupportedProperties")

    run(pytester, "--atomforge-runtime")

    requested = {task.properties for task in requests_made()}
    assert requested == {
        frozenset({Property.ENERGY}),
        frozenset({Property.FORCES}),
        frozenset({Property.ENERGY, Property.FORCES}),
    }


# Outcomes


def test_well_formed_model_passes_every_check_on_all_properties(pytester):
    write_project(pytester)

    found = run(pytester, "--atomforge-runtime")

    assert {check: found[(check, "all")] for check in CHECKS} == {
        check: "PASSED" for check in CHECKS
    }


def test_well_formed_model_fails_nothing(pytester):
    write_project(pytester)

    found = run(pytester, "--atomforge-runtime")

    # Some checks pass; the rest are skipped for properties not requested.
    assert set(found.values()) == {"PASSED", "SKIPPED"}


def test_checks_for_unrequested_properties_are_skipped(pytester):
    write_project(pytester)

    found = run(pytester, "--atomforge-runtime")

    assert found[("test_stress_is_finite", "energy")] == "SKIPPED"


def test_checks_for_undeclared_properties_are_skipped(pytester):
    write_project(pytester, properties="FakeSupportedProperties")

    found = run(pytester, "--atomforge-runtime")

    assert found[("test_stress_is_three_rows_of_three_floats", "all")] == "SKIPPED"


@pytest.mark.parametrize(
    ("executor", "failing"),
    [
        ("MissingForcesExecutor", "test_requested_properties_are_described"),
        ("Float32EnergyExecutor", "test_energy_is_a_float"),
        ("NanEnergyExecutor", "test_energy_is_finite"),
        ("ShortForcesExecutor", "test_forces_have_one_row_per_atom"),
        ("NdarrayForcesExecutor", "test_forces_have_one_row_per_atom"),
        ("NdarrayForcesExecutor", "test_forces_rows_are_three_floats"),
        ("ArrayRowsForcesExecutor", "test_forces_rows_are_three_floats"),
        ("NanForcesExecutor", "test_forces_are_finite"),
        ("VoigtStressExecutor", "test_stress_is_three_rows_of_three_floats"),
        ("ShortEnergiesExecutor", "test_energies_have_one_float_per_atom"),
        ("Float32MagmomsExecutor", "test_magmoms_have_one_float_per_atom"),
    ],
)
def test_each_defect_fails_its_check(pytester, executor, failing):
    write_project(pytester, executor=executor)

    found = run(pytester, "--atomforge-runtime")

    assert found[(failing, "all")] == "FAILED"


@pytest.mark.parametrize(
    ("executor", "passing"),
    [
        # Rows that are arrays still give one row per atom.
        ("ArrayRowsForcesExecutor", "test_forces_have_one_row_per_atom"),
        # A defect in the forces does not fail the energy.
        ("NdarrayForcesExecutor", "test_energy_is_a_float"),
        # np.float64 is a float.
        ("Float64EnergyExecutor", "test_energy_is_a_float"),
    ],
)
def test_check_is_not_failed_by_other_defects(pytester, executor, passing):
    write_project(pytester, executor=executor)

    found = run(pytester, "--atomforge-runtime")

    assert found[(passing, "all")] == "PASSED"


def test_defect_in_one_request_branch_is_found(pytester):
    # Wrong forces only when forces are requested on their own.
    write_project(pytester, executor="BranchingForcesExecutor")

    found = run(pytester, "--atomforge-runtime")

    assert found[("test_forces_rows_are_three_floats", "forces")] == "FAILED"


def test_defect_in_one_request_branch_is_hidden_from_the_others(pytester):
    write_project(pytester, executor="BranchingForcesExecutor")

    found = run(pytester, "--atomforge-runtime")

    assert found[("test_forces_rows_are_three_floats", "all")] == "PASSED"
