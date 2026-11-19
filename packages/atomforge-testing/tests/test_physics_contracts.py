"""Acceptance tests for the physics checks (step 3 of the "Extending
atomforge-testing" design entry in the engineering log).

`ModelPhysicsContract` runs model-independent checks on runtime results,
compared with tolerances per precision. Each test here runs the contract in an
inner pytest session, against a backend that runs a fake executor in process: a
spring potential with exact forces, or a variant broken in one way.
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
from atomforge_testing import ModelPhysics
from atomforge_testing.physics import Tolerances

PYPROJECT = Path(__file__).parent / "pyproject.toml"

MANIFEST = ModelManifest(
    kind="fake-model",
    model_spec="testing_fakes:FakeModel",
    executor_cls="testing_fakes:{executor}",
    supported_properties="testing_fakes:{properties}",
    environment_factory_cls="testing_fakes:FakeEnvironmentFactory",
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
    runtime_exec_resources=ExecutionResources(
        accelerator="cpu", precision="{precision}"
    ),
    tolerances={tolerances},
    physics={physics},
    physics_structures={physics_structures},
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

PHYSICS_TESTS = """\
from fake_case import CASE
from atomforge_testing import ModelPhysicsContract


class TestFake(ModelPhysicsContract):
    manifest_case = CASE
"""

CHECKS = (
    "test_energy_is_invariant_under_translation",
    "test_energy_is_invariant_under_rotation",
    "test_forces_sum_to_zero",
    "test_forces_match_energy_gradient",
    "test_repeated_request_gives_same_result",
    "test_per_atom_energies_sum_to_energy",
    "test_stress_is_symmetric",
)


def write_project(
    pytester,
    *,
    executor="SpringExecutor",
    properties="SpringSupportedProperties",
    capabilities="F32F64Capabilities",
    precision="f64",
    tolerances="None",
    physics="ModelPhysics()",
    physics_structures="None",
):
    pytester.makefile(".toml", pyproject=PYPROJECT)
    pytester.makepyfile(
        fake_case=CASE_MODULE.format(
            executor=executor,
            properties=properties,
            capabilities=capabilities,
            precision=precision,
            tolerances=tolerances,
            physics=physics,
            physics_structures=physics_structures,
        )
    )
    pytester.makeconftest(IN_PROCESS_BACKEND_CONFTEST)
    pytester.makepyfile(test_contracts=PHYSICS_TESTS)
    pytester.syspathinsert()


OUTCOME = re.compile(r"::(\w+)(\[[^\]]*\])? (PASSED|FAILED|SKIPPED|ERROR)")
# Several structures can run one check; a check's outcome is the worst of them.
SEVERITY = {"SKIPPED": 0, "PASSED": 1, "ERROR": 2, "FAILED": 3}


def run_items(pytester, *args) -> dict[str, str]:
    """Outcome per test id, e.g. ``test_stress_is_symmetric[slab]``."""
    result = pytester.runpytest_inprocess("--atomforge-runtime", "-v", *args)
    found = {}
    for line in result.outlines:
        match = OUTCOME.search(line)
        if match:
            found[match.group(1) + (match.group(2) or "")] = match.group(3)
    return found


def run(pytester, *args) -> dict[str, str]:
    """Outcome per check."""
    found = {}
    for item, outcome in run_items(pytester, *args).items():
        name = item.split("[")[0]
        if name not in found or SEVERITY[outcome] > SEVERITY[found[name]]:
            found[name] = outcome
    return found


@pytest.fixture(autouse=True)
def reset_recorders():
    testing_fakes.InProcessBackend.instances = []
    testing_fakes._ForceNoiseExecutor.calls = 0


def requests_made():
    return [
        request
        for backend in testing_fakes.InProcessBackend.instances
        for request in backend.requests
    ]


def test_contract_has_one_test_per_check():
    from atomforge_testing import ModelPhysicsContract

    names = {name for name in dir(ModelPhysicsContract) if name.startswith("test_")}
    assert names == set(CHECKS)


def test_consistent_model_passes_every_check(pytester):
    write_project(pytester)

    assert run(pytester) == {name: "PASSED" for name in CHECKS}


@pytest.mark.parametrize(
    ("executor", "failing"),
    [
        ("WrongSignForcesExecutor", "test_forces_match_energy_gradient"),
        ("NetForceExecutor", "test_forces_sum_to_zero"),
        ("TranslationVariantExecutor", "test_energy_is_invariant_under_translation"),
        ("RotationVariantExecutor", "test_energy_is_invariant_under_rotation"),
        ("LargeForceNoiseExecutor", "test_repeated_request_gives_same_result"),
        ("EnergiesNotSummingExecutor", "test_per_atom_energies_sum_to_energy"),
        ("AsymmetricStressExecutor", "test_stress_is_symmetric"),
    ],
)
def test_each_defect_fails_its_check(pytester, executor, failing):
    write_project(pytester, executor=executor)

    assert run(pytester)[failing] == "FAILED"


def test_rotation_variant_model_is_still_translation_invariant(pytester):
    # The rotation check is not a second translation check.
    write_project(pytester, executor="RotationVariantExecutor")

    found = run(pytester)

    assert found["test_energy_is_invariant_under_translation"] == "PASSED"


def test_results_within_default_tolerance_pass(pytester):
    write_project(pytester, executor="SmallForceNoiseExecutor")

    assert run(pytester) == {name: "PASSED" for name in CHECKS}


def test_f32_run_uses_f32_tolerances(pytester):
    # Twice the f64 force tolerance, far below the f32 one.
    write_project(pytester, executor="LargeForceNoiseExecutor", precision="f32")

    assert run(pytester)["test_repeated_request_gives_same_result"] == "PASSED"


def test_case_tolerances_override_the_defaults(pytester):
    write_project(
        pytester,
        executor="LargeForceNoiseExecutor",
        tolerances=(
            '{"f64": Tolerances(energy_per_atom=1e-6, forces=1e-3, stress=1e-6,'
            " finite_difference=1e-3, finite_difference_step=1e-3)}"
        ),
    )

    assert run(pytester)["test_repeated_request_gives_same_result"] == "PASSED"


def test_default_tolerances_exist_for_both_precisions():
    from atomforge_testing.physics import DEFAULT_TOLERANCES, Tolerances

    assert set(DEFAULT_TOLERANCES) == {"f32", "f64"}
    assert all(isinstance(t, Tolerances) for t in DEFAULT_TOLERANCES.values())
    f32, f64 = DEFAULT_TOLERANCES["f32"], DEFAULT_TOLERANCES["f64"]
    assert f32.energy_per_atom > f64.energy_per_atom
    assert f32.forces > f64.forces


def test_finite_differences_run_in_f64_when_declared(pytester):
    write_project(pytester, precision="f32")

    run(pytester, "-k", "energy_gradient")

    precisions = {resources.precision for _, _, resources in requests_made()}
    assert precisions == {"f64"}


def test_finite_differences_use_the_case_precision_without_f64(pytester):
    write_project(pytester, precision="f32", capabilities="F32OnlyCapabilities")

    found = run(pytester, "-k", "energy_gradient")

    assert found == {"test_forces_match_energy_gradient": "PASSED"}
    precisions = {resources.precision for _, _, resources in requests_made()}
    assert precisions == {"f32"}


def test_checks_of_undeclared_properties_are_skipped(pytester):
    write_project(
        pytester,
        executor="FakeModelExecutor",
        properties="FakeSupportedProperties",
    )

    found = run(pytester)

    assert found["test_per_atom_energies_sum_to_energy"] == "SKIPPED"
    assert found["test_stress_is_symmetric"] == "SKIPPED"


def test_physics_checks_are_runtime_gated(pytester):
    write_project(pytester)

    result = pytester.runpytest_inprocess("-v")

    outcomes = result.parseoutcomes()
    assert set(outcomes) == {"skipped"}
    assert outcomes["skipped"] >= len(CHECKS)
    assert requests_made() == []


def test_bundle_includes_the_physics_contract():
    from atomforge_testing import ModelPhysicsContract, ModelPluginContract

    assert issubclass(ModelPluginContract, ModelPhysicsContract)


# Declared physics: a model that is not conservative, or not invariant under
# rotations or translations, declares it in its case. The checks that rely on
# the property are skipped; a check that follows from two properties (zero net
# force from translation invariance of a conservative model, stress symmetry
# from rotation invariance of a conservative model) needs both.

DECLARATION_SKIPS = {
    "conservative_forces": {
        "test_forces_match_energy_gradient",
        "test_forces_sum_to_zero",
        "test_stress_is_symmetric",
    },
    "translation_invariant": {
        "test_energy_is_invariant_under_translation",
        "test_forces_sum_to_zero",
    },
    "rotation_invariant": {
        "test_energy_is_invariant_under_rotation",
        "test_stress_is_symmetric",
    },
}


def test_default_declaration_claims_every_property():
    from atomforge_testing import ModelManifestCase, ModelPhysics

    physics = ModelPhysics()
    assert physics.conservative_forces
    assert physics.translation_invariant
    assert physics.rotation_invariant
    field = ModelManifestCase.__dataclass_fields__["physics"]
    assert field.default == physics


@pytest.mark.parametrize("declaration", sorted(DECLARATION_SKIPS))
def test_declaring_a_property_absent_skips_its_checks(pytester, declaration):
    write_project(pytester, physics=f"ModelPhysics({declaration}=False)")

    found = run(pytester)

    skipped = DECLARATION_SKIPS[declaration]
    assert found == {
        name: "SKIPPED" if name in skipped else "PASSED" for name in CHECKS
    }


@pytest.mark.parametrize(
    ("executor", "declaration"),
    [
        ("WrongSignForcesExecutor", "conservative_forces"),
        ("TranslationVariantExecutor", "translation_invariant"),
        ("RotationVariantExecutor", "rotation_invariant"),
    ],
)
def test_declared_model_is_not_failed_for_the_declared_property(
    pytester, executor, declaration
):
    write_project(
        pytester, executor=executor, physics=f"ModelPhysics({declaration}=False)"
    )

    found = run(pytester)

    assert "FAILED" not in found.values()


def test_skip_reason_names_the_declaration(pytester):
    write_project(pytester, physics="ModelPhysics(rotation_invariant=False)")

    result = pytester.runpytest_inprocess("--atomforge-runtime", "-rs")

    result.stdout.fnmatch_lines(["*rotation_invariant=False*"])


def test_skipped_checks_make_no_requests(pytester):
    write_project(pytester, physics="ModelPhysics(conservative_forces=False)")

    run(pytester, "-k", "energy_gradient")

    assert requests_made() == []


# Finite differences are checked on the largest force components, and a check
# whose forces are all too small to tell a wrong sign from a right one fails
# as uninformative instead of passing.


def test_gradient_check_uses_the_largest_force_components(pytester):
    write_project(pytester, executor="HiddenWrongSignExecutor")

    assert run(pytester, "-k", "energy_gradient") == {
        "test_forces_match_energy_gradient": "FAILED"
    }


def test_gradient_check_fails_when_forces_are_too_small_to_check(pytester):
    write_project(pytester, executor="WeakSpringExecutor")

    result = pytester.runpytest_inprocess(
        "--atomforge-runtime", "-k", "energy_gradient"
    )

    result.assert_outcomes(failed=3)
    result.stdout.fnmatch_lines(["*uninformative*"])


# The physics checks run on the reference structures (a molecule, a slab and a
# bulk crystal) unless the case replaces them.

ELEMENTS = {
    "molecule": frozenset({1, 6, 8}),
    "slab": frozenset({29}),
    "bulk": frozenset({14}),
}


def structures_requested():
    found = set()
    for task, _, _ in requests_made():
        elements = frozenset(task.structure.numbers)
        found |= {name for name, e in ELEMENTS.items() if e == elements}
    return found


def test_physics_checks_run_on_the_reference_structures(pytester):
    write_project(pytester)

    run(pytester)

    assert structures_requested() == set(ELEMENTS)


@pytest.mark.parametrize(
    ("check", "expected"),
    [
        ("invariant_under_rotation", {"molecule"}),
        ("sum_to_zero", {"molecule"}),
        ("stress_is_symmetric", {"slab", "bulk"}),
        ("invariant_under_translation", {"molecule", "slab", "bulk"}),
        ("energy_gradient", {"molecule", "slab", "bulk"}),
    ],
)
def test_each_check_runs_on_the_structures_it_applies_to(pytester, check, expected):
    write_project(pytester)

    run(pytester, "-k", check)

    assert structures_requested() == expected


def test_case_can_replace_the_physics_structures(pytester):
    write_project(
        pytester,
        physics_structures=(
            '{"molecule": __import__("atomforge_testing.structures")'
            ".structures.ethanol()}"
        ),
    )

    found = run(pytester)

    assert structures_requested() == {"molecule"}
    assert found["test_stress_is_symmetric"] == "SKIPPED"
    assert found["test_energy_is_invariant_under_rotation"] == "PASSED"


def test_case_rejects_unknown_physics_structure_names():
    from atomforge_testing import ModelManifestCase
    from atomforge_testing.structures import ethanol

    with pytest.raises(ValueError, match="crystal"):
        ModelManifestCase(
            manifest=None,
            entry_point_name="fake",
            entry_point_package="fake-plugin",
            pyproject_path=TESTS_PATH,
            expected_entry_point_target="testing_fakes:fake_manifest",
            physics_structures={"crystal": ethanol()},
        )
