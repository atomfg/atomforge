"""Acceptance tests for running the runtime contracts once per environment
profile (step 4 of the "Extending atomforge-testing" design entry, as revised
in "atomforge-testing step 4, revised design", in the engineering log).

The single-point and physics contracts are parametrized by the profiles the
model spec allows, as the environment contracts already are, and run the model
with that profile.
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
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_testing import ModelManifestCase

PYPROJECT = Path(__file__).parent / "pyproject.toml"

CASE = ModelManifestCase(
    manifest=ModelManifest(
        kind="fake-model",
        model_spec="testing_fakes:{model_spec}",
        executor_cls="testing_fakes:{executor}",
        supported_properties="testing_fakes:SpringSupportedProperties",
        environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
        metadata="testing_fakes:FakeMetadata",
        resource_capabilities="testing_fakes:F32F64Capabilities",
        distribution="fake-plugin",
    ),
    entry_point_name="fake",
    entry_point_package="fake-plugin",
    pyproject_path=PYPROJECT,
    expected_entry_point_target="testing_fakes:fake_manifest",
    runtime_exec_resources=ExecutionResources(accelerator="cpu", precision="f64"),
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
from atomforge_testing import ModelPhysicsContract, ModelSinglePointRuntimeContract


class TestFake(ModelSinglePointRuntimeContract, ModelPhysicsContract):
    manifest_case = CASE
"""

RUNTIME_TEST_NAMES = (
    "test_declared_property_is_returned",
    "test_declared_resources_execute_strictly",
    "test_energy_is_invariant_under_translation",
    "test_energy_is_invariant_under_rotation",
    "test_forces_sum_to_zero",
    "test_forces_match_energy_gradient",
    "test_repeated_request_gives_same_result",
    "test_per_atom_energies_sum_to_energy",
    "test_stress_is_symmetric",
)


def write_project(pytester, *, model_spec="ProfiledFakeModel", executor):
    pytester.makefile(".toml", pyproject=PYPROJECT)
    pytester.makepyfile(
        fake_case=CASE_MODULE.format(model_spec=model_spec, executor=executor)
    )
    pytester.makeconftest(IN_PROCESS_BACKEND_CONFTEST)
    pytester.makepyfile(test_contracts=RUNTIME_TESTS)
    pytester.syspathinsert()


OUTCOME = re.compile(r"::(\w+)\[([^\]]*)\] (PASSED|FAILED|SKIPPED|ERROR)")


def run(pytester, *args) -> dict[tuple[str, str], str]:
    """Outcome per (test name, parameter id)."""
    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v", *args)
    found = {}
    for line in result.outlines:
        match = OUTCOME.search(line)
        if match:
            found[(match.group(1), match.group(2))] = match.group(3)
    return found


@pytest.fixture(autouse=True)
def reset_recorders():
    testing_fakes.InProcessBackend.instances = []


def requests_made():
    return [
        request
        for backend in testing_fakes.InProcessBackend.instances
        for request in backend.requests
    ]


def test_every_runtime_test_runs_once_per_profile(pytester):
    write_project(pytester, executor="SpringExecutor")

    found = run(pytester)

    for name in RUNTIME_TEST_NAMES:
        profiles = {param.split("-")[0] for test, param in found if test == name}
        assert profiles == {"tested", "latest"}, name


def test_profile_comes_first_in_the_test_id(pytester):
    write_project(pytester, executor="SpringExecutor")

    found = run(pytester)

    assert ("test_declared_property_is_returned", "latest-stress") in found
    assert ("test_declared_resources_execute_strictly", "latest-cpu-f64") in found
    assert ("test_forces_match_energy_gradient", "latest-bulk") in found


def test_each_profile_runs_the_model_with_that_profile(pytester):
    write_project(pytester, executor="SpringExecutor")

    run(pytester, "-k", "latest")

    profiles = {model.environment_profile for _, model, _ in requests_made()}
    assert profiles == {"latest"}


def test_broken_latest_profile_fails_only_latest_tests(pytester):
    write_project(pytester, executor="LatestWrongSignExecutor")

    found = run(pytester, "-k", "energy_gradient")

    assert found == {
        ("test_forces_match_energy_gradient", f"{profile}-{structure}"): (
            "FAILED" if profile == "latest" else "PASSED"
        )
        for profile in ("tested", "latest")
        for structure in ("molecule", "slab", "bulk")
    }


def test_spec_without_profile_literal_runs_tested_only(pytester):
    write_project(pytester, model_spec="FakeModel", executor="SpringExecutor")

    found = run(pytester)

    assert found
    assert {param.split("-")[0] for _, param in found} == {"tested"}
