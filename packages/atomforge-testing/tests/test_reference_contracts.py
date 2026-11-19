"""Acceptance tests for the reference contract (step 4 of the "Extending
atomforge-testing" design entry, as revised in "atomforge-testing step 4,
revised design", in the engineering log).

`ModelReferenceContract` compares a model's results on the physics structures
with references stored next to the plugin's tests, through pytest-regressions'
`ndarrays_regression`. A reference is recorded on CPU with the tested profile
at the highest declared precision; every run compares against it with the
reference tolerances. Each test here runs the contract in an inner pytest
session, against a backend that runs a fake executor in process.
"""

from pathlib import Path
import re
import sys

import numpy as np
import pytest

TESTS_PATH = Path(__file__).resolve().parent

if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))

import testing_fakes  # noqa: E402

PYPROJECT = """\
[project]
name = "fake-plugin"

[project.entry-points.'atomforge.model']
fake = "testing_fakes:fake_manifest"
"""

CASE_MODULE = """\
from pathlib import Path

from atomforge_core.registry.model_manifest import ModelManifest
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_testing import ModelManifestCase
from atomforge_testing.physics import ReferenceTolerances

PYPROJECT = Path(__file__).parent / "pyproject.toml"


def manifest(kind, model_spec):
    return ModelManifest(
        kind=kind,
        model_spec=f"testing_fakes:{{model_spec}}",
        executor_cls="testing_fakes:{executor}",
        supported_properties="testing_fakes:{properties}",
        environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
        metadata="testing_fakes:FakeMetadata",
        resource_capabilities="testing_fakes:{capabilities}",
        distribution="fake-plugin",
    )


def case(kind, model_spec):
    return ModelManifestCase(
        manifest=manifest(kind, model_spec),
        entry_point_name="fake",
        entry_point_package="fake-plugin",
        pyproject_path=PYPROJECT,
        expected_entry_point_target="testing_fakes:fake_manifest",
        runtime_exec_resources=ExecutionResources(
            accelerator="cpu", precision="{precision}"
        ),
        reference_tolerances={reference_tolerances},
        physics_structures={physics_structures},
    )


CASE = case("fake-model", "{model_spec}")
OTHER_CASE = case("other-fake-model", "OtherKindFakeModel")
"""

IN_PROCESS_BACKEND_CONFTEST = """\
import pytest

from fake_case import CASE
from testing_fakes import InProcessBackend


@pytest.fixture(scope="session")
def atomforge_backend():
    return InProcessBackend(CASE.manifest)
"""

REFERENCE_TESTS = """\
from fake_case import CASE
from atomforge_testing import ModelReferenceContract


class TestFake(ModelReferenceContract):
    manifest_case = CASE
"""

TWO_KINDS_TESTS = """\
from fake_case import CASE, OTHER_CASE
from atomforge_testing import ModelReferenceContract


class TestFake(ModelReferenceContract):
    manifest_case = CASE


class TestOtherFake(ModelReferenceContract):
    manifest_case = OTHER_CASE
"""

TEST = "test_matches_reference"
STRUCTURES = ("molecule", "slab", "bulk")


def write_project(
    pytester,
    *,
    tests=REFERENCE_TESTS,
    model_spec="FakeModel",
    executor="ShiftedSpringExecutor",
    properties="EnergyForcesStress",
    capabilities="F32F64Capabilities",
    precision="f64",
    reference_tolerances="None",
    physics_structures="None",
):
    pytester.makefile(".toml", pyproject=PYPROJECT)
    pytester.makepyfile(
        fake_case=CASE_MODULE.format(
            model_spec=model_spec,
            executor=executor,
            properties=properties,
            capabilities=capabilities,
            precision=precision,
            reference_tolerances=reference_tolerances,
            physics_structures=physics_structures,
        )
    )
    pytester.makeconftest(IN_PROCESS_BACKEND_CONFTEST)
    pytester.makepyfile(test_contracts=tests)
    pytester.syspathinsert()


OUTCOME = re.compile(r"::(\w+)::(\w+)(\[[^\]]*\])? (PASSED|FAILED|SKIPPED|ERROR)")


def run(pytester, *args):
    """The inner session's result, and the outcome per parameter id of the
    reference test (prefixed with the class name when there are several)."""
    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v", *args)
    found = {}
    for line in result.outlines:
        match = OUTCOME.search(line)
        if match and match.group(2) == TEST:
            found[(match.group(1), (match.group(3) or "")[1:-1])] = match.group(4)
    classes = {cls for cls, _ in found}
    if len(classes) == 1:
        found = {param: outcome for (_, param), outcome in found.items()}
    return result, found


def reference_file(pytester, kind, structure):
    return pytester.path / "test_contracts" / f"{kind}-{structure}.npz"


def load(path):
    with np.load(path) as data:
        return {key: data[key] for key in data.files}


@pytest.fixture(autouse=True)
def reset_recorders():
    testing_fakes.InProcessBackend.instances = []
    testing_fakes.ShiftedSpringExecutor.shifts = {}
    testing_fakes.ShiftedSpringExecutor.f32_shifts = {}


def requests_made():
    return [
        request
        for backend in testing_fakes.InProcessBackend.instances
        for request in backend.requests
    ]


def clear_requests():
    for backend in testing_fakes.InProcessBackend.instances:
        backend.requests.clear()


def tolerance(field):
    from atomforge_testing.physics import REFERENCE_TOLERANCES

    return getattr(REFERENCE_TOLERANCES, field)


def record(pytester, *args):
    """Run once to write the references, and check that it did."""
    _, found = run(pytester, *args)
    assert found and set(found.values()) == {"FAILED"}, found
    clear_requests()


# The contract


def test_contract_has_one_test():
    from atomforge_testing import ModelReferenceContract

    names = {name for name in dir(ModelReferenceContract) if name.startswith("test_")}
    assert names == {TEST}


def test_bundle_includes_the_reference_contract():
    from atomforge_testing import ModelPluginContract, ModelReferenceContract

    assert issubclass(ModelPluginContract, ModelReferenceContract)


def test_reference_tolerances_are_measured_values():
    from atomforge_testing.physics import REFERENCE_TOLERANCES, ReferenceTolerances

    assert isinstance(REFERENCE_TOLERANCES, ReferenceTolerances)
    assert REFERENCE_TOLERANCES.energy_per_atom > 0
    assert REFERENCE_TOLERANCES.forces > 0
    assert REFERENCE_TOLERANCES.stress > 0


def test_reference_tests_are_runtime_gated(pytester):
    write_project(pytester)

    result = pytester.runpytest_inprocess("-v")

    outcomes = result.parseoutcomes()
    assert set(outcomes) == {"skipped"}
    assert requests_made() == []
    assert not (pytester.path / "test_contracts").exists()


def test_one_test_per_profile_and_structure(pytester):
    write_project(pytester, model_spec="ProfiledFakeModel")

    _, found = run(pytester)

    assert set(found) == {
        f"{profile}-{structure}"
        for profile in ("tested", "latest")
        for structure in STRUCTURES
    }


# Recording


def test_missing_reference_fails_and_writes_it(pytester):
    write_project(pytester)

    result, found = run(pytester)

    assert found == {f"tested-{s}": "FAILED" for s in STRUCTURES}
    for structure in STRUCTURES:
        assert reference_file(pytester, "fake-model", structure).is_file()
    result.stdout.fnmatch_lines(["*fake-model-molecule.npz*"])


def test_reference_holds_energy_per_atom_forces_and_stress(pytester):
    write_project(pytester)

    run(pytester)

    molecule = load(reference_file(pytester, "fake-model", "molecule"))
    bulk = load(reference_file(pytester, "fake-model", "bulk"))
    assert set(molecule) == {"energy_per_atom", "forces"}
    assert set(bulk) == {"energy_per_atom", "forces", "stress"}
    assert molecule["forces"].shape == (9, 3)
    assert bulk["stress"].shape == (3, 3)


def test_reference_has_no_stress_when_undeclared(pytester):
    write_project(
        pytester, executor="SpringExecutor", properties="FakeSupportedProperties"
    )

    run(pytester)

    bulk = load(reference_file(pytester, "fake-model", "bulk"))
    assert set(bulk) == {"energy_per_atom", "forces"}


def test_reference_is_recorded_on_cpu_at_the_highest_precision(pytester):
    # The case runs in f32; the reference is recorded in f64.
    write_project(pytester, precision="f32")

    run(pytester)

    recorded = {
        (resources.accelerator, resources.precision, model.environment_profile)
        for _, model, resources in requests_made()
    }
    assert recorded == {("cpu", "f64", "tested")}


def test_reference_is_recorded_in_f32_without_f64(pytester):
    write_project(pytester, precision="f32", capabilities="F32OnlyCapabilities")

    run(pytester)

    precisions = {resources.precision for _, _, resources in requests_made()}
    assert precisions == {"f32"}


def test_reference_in_place_passes(pytester):
    write_project(pytester)
    record(pytester)

    _, found = run(pytester)

    assert found == {f"tested-{s}": "PASSED" for s in STRUCTURES}


def test_comparison_runs_with_the_case_resources(pytester):
    write_project(pytester, precision="f32")
    record(pytester)

    run(pytester)

    precisions = {resources.precision for _, _, resources in requests_made()}
    assert precisions == {"f32"}


def test_two_kinds_in_one_module_write_separate_files(pytester):
    write_project(pytester, tests=TWO_KINDS_TESTS)

    run(pytester)

    for kind in ("fake-model", "other-fake-model"):
        for structure in STRUCTURES:
            assert reference_file(pytester, kind, structure).is_file()


def test_references_follow_the_physics_structures(pytester):
    write_project(
        pytester,
        physics_structures=(
            '{"molecule": __import__("atomforge_testing.structures")'
            ".structures.ethanol()}"
        ),
    )

    _, found = run(pytester)

    assert found["tested-molecule"] == "FAILED"
    assert found["tested-slab"] == found["tested-bulk"] == "SKIPPED"
    assert not reference_file(pytester, "fake-model", "slab").exists()


# Comparing


@pytest.mark.parametrize("field", ["energy_per_atom", "forces", "stress"])
def test_result_beyond_tolerance_fails(pytester, field):
    write_project(pytester)
    record(pytester)
    testing_fakes.ShiftedSpringExecutor.shifts = {field: 2 * tolerance(field)}

    _, found = run(pytester)

    assert "FAILED" in found.values()
    if field == "stress":
        assert found["tested-molecule"] == "PASSED"


@pytest.mark.parametrize("field", ["energy_per_atom", "forces", "stress"])
def test_result_within_tolerance_passes(pytester, field):
    write_project(pytester)
    record(pytester)
    testing_fakes.ShiftedSpringExecutor.shifts = {field: 0.5 * tolerance(field)}

    _, found = run(pytester)

    assert set(found.values()) == {"PASSED"}


def test_f32_result_within_tolerance_of_f64_reference_passes(pytester):
    write_project(pytester, precision="f32")
    testing_fakes.ShiftedSpringExecutor.f32_shifts = {
        "forces": 0.5 * tolerance("forces")
    }
    record(pytester)

    _, found = run(pytester)

    assert set(found.values()) == {"PASSED"}


def test_comparison_has_no_relative_term(pytester):
    # With a force tolerance of zero, a shift far below numpy's default
    # relative tolerance (1e-5 of forces of order 1 eV/Å) still fails.
    write_project(
        pytester,
        reference_tolerances=(
            "ReferenceTolerances(energy_per_atom=1e-5, forces=0.0, stress=3e-5)"
        ),
    )
    record(pytester, "-k", "molecule")
    testing_fakes.ShiftedSpringExecutor.shifts = {"forces": 1e-9}

    _, found = run(pytester, "-k", "molecule")

    assert found == {"tested-molecule": "FAILED"}


def test_case_reference_tolerances_override_the_defaults(pytester):
    write_project(
        pytester,
        reference_tolerances=(
            "ReferenceTolerances(energy_per_atom=1e-5, forces=1e-2, stress=3e-5)"
        ),
    )
    record(pytester)
    testing_fakes.ShiftedSpringExecutor.shifts = {"forces": 2 * tolerance("forces")}

    _, found = run(pytester)

    assert set(found.values()) == {"PASSED"}


# Other profiles


def test_latest_without_reference_fails_without_writing(pytester):
    write_project(pytester, model_spec="ProfiledFakeModel")

    result, found = run(pytester, "-k", "latest")

    assert found == {f"latest-{s}": "FAILED" for s in STRUCTURES}
    assert not (pytester.path / "test_contracts").exists()
    result.stdout.fnmatch_lines(["*tested-molecule*"])


def test_latest_compares_against_the_tested_reference(pytester):
    write_project(pytester, model_spec="ProfiledFakeModel")
    record(pytester, "-k", "tested")

    _, found = run(pytester)

    assert set(found.values()) == {"PASSED"}
    profiles = {model.environment_profile for _, model, _ in requests_made()}
    assert profiles == {"tested", "latest"}


# Regenerating


def test_force_regen_rewrites_from_reference_conditions(pytester):
    write_project(pytester, model_spec="ProfiledFakeModel", precision="f32")
    record(pytester, "-k", "tested")
    shift = 2 * tolerance("forces")
    testing_fakes.ShiftedSpringExecutor.shifts = {"forces": shift}
    path = reference_file(pytester, "fake-model", "molecule")
    before = load(path)["forces"]

    _, found = run(pytester, "--force-regen")

    assert {found[f"tested-{s}"] for s in STRUCTURES} == {"FAILED"}
    assert {found[f"latest-{s}"] for s in STRUCTURES} == {"SKIPPED"}
    assert np.allclose(load(path)["forces"], before + shift, rtol=0, atol=1e-12)
    recorded = {
        (resources.precision, model.environment_profile)
        for _, model, resources in requests_made()
    }
    assert recorded == {("f64", "tested")}


# The optional extra


def test_missing_pytest_regressions_fails_with_the_extra_named(pytester):
    write_project(pytester)

    result, found = run(pytester, "-p", "no:regressions")

    assert set(found.values()) == {"FAILED"}
    result.stdout.fnmatch_lines(["*atomforge-testing[[]regression[]]*"])
