"""Acceptance tests for the capability contracts (step 2 of the "Extending
atomforge-testing" design entry in the engineering log).

The contracts are parametrized from the case's manifest: one test per declared
property, per declared resource combination and per environment profile. Each
test here runs the contracts in an inner pytest session, against a backend
that runs the fake model executor in process.
"""

from pathlib import Path
import re
import sys

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
from atomforge_testing import ModelManifestCase, structures

PYPROJECT = Path(__file__).parent / "pyproject.toml"

MANIFEST = ModelManifest(
    kind="fake-model",
    model_spec="testing_fakes:{model_spec}",
    executor_cls="testing_fakes:{executor}",
    supported_properties="testing_fakes:{properties}",
    environment_factory_cls="testing_fakes:{environment_factory}",
    metadata="testing_fakes:FakeMetadata",
    resource_capabilities="testing_fakes:{capabilities}",
    distribution="fake-plugin",
)

CASE = ModelManifestCase(
    manifest=MANIFEST,
    entry_point_name="fake",
    entry_point_package="fake-plugin",
    pyproject_path=PYPROJECT,
    expected_entry_point_target="testing_fakes:fake_manifest",
    runtime_structure={runtime_structure},
)
"""

IN_PROCESS_BACKEND_CONFTEST = """\
import pytest

from fake_case import CASE
from testing_fakes import InProcessBackend


@pytest.fixture(scope="session")
def atomforge_backend():
    return InProcessBackend(CASE.manifest)
"""

RUNTIME_TESTS = """\
from fake_case import CASE
from atomforge_testing import ModelSinglePointRuntimeContract


class TestFake(ModelSinglePointRuntimeContract):
    manifest_case = CASE
"""

ENVIRONMENT_TESTS = """\
from fake_case import CASE
from atomforge_testing import (
    ModelEnvironmentContract,
    ModelEnvironmentResolutionContract,
)


class TestFake(ModelEnvironmentContract, ModelEnvironmentResolutionContract):
    manifest_case = CASE
"""


def write_project(
    pytester,
    tests: str,
    *,
    model_spec="FakeModel",
    executor="AllPropertiesExecutor",
    properties="AllSupportedProperties",
    environment_factory="FakeEnvironmentFactory",
    capabilities="FakeResourceCapabilities",
    runtime_structure="None",
):
    pytester.makefile(".toml", pyproject=PYPROJECT)
    pytester.makepyfile(
        fake_case=CASE_MODULE.format(
            model_spec=model_spec,
            executor=executor,
            properties=properties,
            environment_factory=environment_factory,
            capabilities=capabilities,
            runtime_structure=runtime_structure,
        )
    )
    pytester.makeconftest(IN_PROCESS_BACKEND_CONFTEST)
    pytester.makepyfile(test_contracts=tests)
    pytester.syspathinsert()


OUTCOME = re.compile(r"::(\w+(?:\[[^\]]*\])?) (PASSED|FAILED|SKIPPED|ERROR)")


def outcomes(result) -> dict[str, str]:
    """Outcome of each test, keyed by test name and parameter id."""
    found = {}
    for line in result.outlines:
        match = OUTCOME.search(line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def matching(found: dict[str, str], test_name: str) -> dict[str, str]:
    """Outcomes of one contract test, keyed by parameter id."""
    prefix = f"{test_name}["
    return {
        name[len(prefix) : -1]: outcome
        for name, outcome in found.items()
        if name.startswith(prefix)
    }


@pytest.fixture(autouse=True)
def reset_recorders():
    testing_fakes.InProcessBackend.instances = []
    testing_fakes.ProfileNamedEnvironmentFactory.seen_profiles = []


def requests_made():
    return [
        request
        for backend in testing_fakes.InProcessBackend.instances
        for request in backend.requests
    ]


# Properties

PROPERTY_TEST = "test_declared_property_is_returned"


def test_one_property_test_per_declared_property(pytester):
    write_project(pytester, RUNTIME_TESTS)

    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v")

    assert matching(outcomes(result), PROPERTY_TEST) == {
        "tested-energy": "PASSED",
        "tested-forces": "PASSED",
        "tested-stress": "PASSED",
        "tested-energies": "PASSED",
        "tested-magmoms": "PASSED",
    }


def test_only_declared_properties_are_tested(pytester):
    write_project(
        pytester,
        RUNTIME_TESTS,
        executor="FakeModelExecutor",
        properties="FakeSupportedProperties",
    )

    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v")

    assert matching(outcomes(result), PROPERTY_TEST) == {
        "tested-energy": "PASSED",
        "tested-forces": "PASSED",
    }


def test_each_property_is_requested_alone(pytester):
    write_project(pytester, RUNTIME_TESTS)

    pytester.runpytest_inprocess("--atomforge-runtime", "-k", PROPERTY_TEST)

    requested = sorted(
        sorted(p.value for p in task.properties) for task, _, _ in requests_made()
    )
    assert requested == [
        ["energies"],
        ["energy"],
        ["forces"],
        ["magmoms"],
        ["stress"],
    ]


def test_stress_is_requested_on_a_periodic_structure(pytester):
    # The case's runtime structure is a molecule; stress needs a cell.
    write_project(
        pytester, RUNTIME_TESTS, runtime_structure="structures.small_molecule()"
    )

    pytester.runpytest_inprocess("--atomforge-runtime", "-k", "stress")

    stress_tasks = [
        task
        for task, _, _ in requests_made()
        if task.properties == frozenset({testing_fakes.Property.STRESS})
    ]
    assert stress_tasks
    assert all(any(task.structure.pbc) for task in stress_tasks)


@pytest.mark.parametrize(
    ("executor", "failing"),
    [
        ("NoneStressExecutor", "stress"),
        ("ShortEnergiesExecutor", "energies"),
        ("VoigtStressExecutor", "stress"),
        ("NanEnergyExecutor", "energy"),
    ],
)
def test_malformed_property_fails_its_own_test(pytester, executor, failing):
    write_project(pytester, RUNTIME_TESTS, executor=executor)

    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v")

    found = matching(outcomes(result), PROPERTY_TEST)
    assert found.pop(f"tested-{failing}") == "FAILED"
    assert set(found.values()) == {"PASSED"}


def test_property_tests_are_runtime_gated(pytester):
    write_project(pytester, RUNTIME_TESTS)

    result = pytester.runpytest_inprocess("-v")

    found = matching(outcomes(result), PROPERTY_TEST)
    assert found and set(found.values()) == {"SKIPPED"}
    assert requests_made() == []


# Resources

RESOURCES_TEST = "test_declared_resources_execute_strictly"


def test_cpu_combinations_run_and_cuda_needs_its_option(pytester):
    write_project(pytester, RUNTIME_TESTS, capabilities="CpuCudaF32F64Capabilities")

    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v")

    assert matching(outcomes(result), RESOURCES_TEST) == {
        "tested-cpu-f32": "PASSED",
        "tested-cpu-f64": "PASSED",
        "tested-cuda-f32": "SKIPPED",
        "tested-cuda-f64": "SKIPPED",
    }


def test_cuda_combinations_run_with_cuda_option(pytester):
    write_project(pytester, RUNTIME_TESTS, capabilities="CpuCudaF32F64Capabilities")

    result = pytester.runpytest_inprocess(
        "--atomforge-runtime", "--atomforge-cuda", "-v"
    )

    assert set(matching(outcomes(result), RESOURCES_TEST).values()) == {"PASSED"}


def test_mps_needs_its_own_option(pytester):
    write_project(pytester, RUNTIME_TESTS, capabilities="CpuMpsCapabilities")

    cuda_only = pytester.runpytest_inprocess(
        "--atomforge-runtime", "--atomforge-cuda", "-v"
    )
    with_mps = pytester.runpytest_inprocess(
        "--atomforge-runtime", "--atomforge-mps", "-v"
    )

    assert matching(outcomes(cuda_only), RESOURCES_TEST) == {
        "tested-cpu-f32": "PASSED",
        "tested-mps-f32": "SKIPPED",
    }
    assert matching(outcomes(with_mps), RESOURCES_TEST) == {
        "tested-cpu-f32": "PASSED",
        "tested-mps-f32": "PASSED",
    }


def test_rocm_needs_its_own_option(pytester):
    write_project(pytester, RUNTIME_TESTS, capabilities="CpuRocmCapabilities")

    cuda_only = pytester.runpytest_inprocess(
        "--atomforge-runtime", "--atomforge-cuda", "-v"
    )
    with_rocm = pytester.runpytest_inprocess(
        "--atomforge-runtime", "--atomforge-rocm", "-v"
    )

    assert matching(outcomes(cuda_only), RESOURCES_TEST) == {
        "tested-cpu-f32": "PASSED",
        "tested-rocm-f32": "SKIPPED",
    }
    assert matching(outcomes(with_rocm), RESOURCES_TEST) == {
        "tested-cpu-f32": "PASSED",
        "tested-rocm-f32": "PASSED",
    }


def test_only_declared_pairs_are_tested(pytester):
    # Precision per accelerator: MPS has no f64, so there is no mps-f64 test.
    write_project(pytester, RUNTIME_TESTS, capabilities="CpuF64MpsF32Capabilities")

    result = pytester.runpytest_inprocess(
        "--atomforge-runtime", "--atomforge-mps", "-v"
    )

    assert matching(outcomes(result), RESOURCES_TEST) == {
        "tested-cpu-f32": "PASSED",
        "tested-cpu-f64": "PASSED",
        "tested-mps-f32": "PASSED",
    }


def test_resources_are_requested_strictly(pytester):
    write_project(pytester, RUNTIME_TESTS, capabilities="CpuCudaF32F64Capabilities")

    pytester.runpytest_inprocess("--atomforge-runtime", "-k", RESOURCES_TEST)

    requested = sorted(
        (resources.accelerator, resources.precision, resources.strict)
        for _, _, resources in requests_made()
    )
    assert requested == [("cpu", "f32", True), ("cpu", "f64", True)]


def test_undeclared_precision_uses_the_default(pytester):
    write_project(
        pytester, RUNTIME_TESTS, capabilities="CpuWithoutPrecisionCapabilities"
    )

    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v")

    assert matching(outcomes(result), RESOURCES_TEST) == {
        "tested-cpu-default": "PASSED"
    }


def test_declared_precision_that_fails_strictly_fails_its_test(pytester):
    write_project(
        pytester,
        RUNTIME_TESTS,
        executor="F64FailingExecutor",
        capabilities="CpuCudaF32F64Capabilities",
    )

    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v")

    found = matching(outcomes(result), RESOURCES_TEST)
    assert found["tested-cpu-f32"] == "PASSED"
    assert found["tested-cpu-f64"] == "FAILED"


# Environment profiles

ENVIRONMENT_TESTS_NAMES = (
    "test_environment_factory_builds_model_environment",
    "test_environment_factory_is_deterministic_for_model_spec",
    "test_environment_provider_requirements_include_entry_point_package",
    "test_environment_requirements_are_declared_in_dependency_summary",
    "test_environment_python_matches_dependency_summary",
    "test_environment_channels_include_dependency_summary_channels",
)


def test_environment_contracts_run_once_per_profile(pytester):
    write_project(
        pytester,
        ENVIRONMENT_TESTS,
        model_spec="ProfiledFakeModel",
        environment_factory="ProfileNamedEnvironmentFactory",
    )

    result = pytester.runpytest_inprocess("-v")

    found = outcomes(result)
    for name in ENVIRONMENT_TESTS_NAMES:
        assert matching(found, name) == {
            "tested": "PASSED",
            "latest": "PASSED",
        }, name
    seen = testing_fakes.ProfileNamedEnvironmentFactory.seen_profiles
    assert set(seen) == {"tested", "latest"}


def test_spec_without_profile_literal_is_tested_profile_only(pytester):
    write_project(pytester, ENVIRONMENT_TESTS)

    result = pytester.runpytest_inprocess("-v")

    found = outcomes(result)
    for name in ENVIRONMENT_TESTS_NAMES:
        assert matching(found, name) == {"tested": "PASSED"}, name


def test_broken_latest_profile_fails_tests_named_latest(pytester):
    write_project(
        pytester,
        ENVIRONMENT_TESTS,
        model_spec="ProfiledFakeModel",
        environment_factory="LatestBrokenEnvironmentFactory",
    )

    result = pytester.runpytest_inprocess("-v")

    found = matching(
        outcomes(result), "test_environment_factory_builds_model_environment"
    )
    assert found == {"tested": "PASSED", "latest": "FAILED"}


class FakeResolutionResult:
    success = True
    provider = "fake"
    command = ("fake", "resolve")
    project_path = Path("/tmp/fake-project")
    message = None
    stdout = ""
    stderr = ""


class RecordingUVEnvironmentProvider:
    resolved: list = []

    def __init__(self, *args, **kwargs):
        pass

    def resolve_environment(self, spec):
        type(self).resolved.append(spec)
        return FakeResolutionResult()


def test_resolution_runs_once_per_profile(pytester, monkeypatch):
    import atomforge.env.uv

    RecordingUVEnvironmentProvider.resolved = []
    monkeypatch.setattr(
        atomforge.env.uv, "UVEnvironmentProvider", RecordingUVEnvironmentProvider
    )
    write_project(
        pytester,
        ENVIRONMENT_TESTS,
        model_spec="ProfiledFakeModel",
        environment_factory="ProfileNamedEnvironmentFactory",
    )

    result = pytester.runpytest_inprocess("--atomforge-environment", "-v")

    found = matching(
        outcomes(result), "test_environment_resolves_with_default_provider"
    )
    assert found == {"tested": "PASSED", "latest": "PASSED"}
    resolved = sorted(spec.name for spec in RecordingUVEnvironmentProvider.resolved)
    assert resolved == ["fake-latest", "fake-tested"]
